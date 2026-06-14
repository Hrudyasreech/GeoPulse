from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import requests 
from collections import defaultdict
from datetime import datetime, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv
load_dotenv()


# Internal modules
from summarizer import generate_ai_insight
from sentiment import get_sentiment
from ner import extract_entities
from category import classify_category
from database import SessionLocal, engine
import models
from config.states import STATE_QUERIES

app = FastAPI()
models.Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


API_key = os.environ.get("API_KEY")

def process_heavy_ai_analytics(state: str, analyzed_articles: list):
    """
    Handles only the heaviest tasks (NER extraction and LLM text generation)
    off the main thread.
    """
    db = SessionLocal()
    try:
        all_extracted_entities = []
        category_counts = {}
        total_score = 0

        for art_data in analyzed_articles:
            text_block = f"{art_data['title']} {art_data['summary']}"
            
            # Count categories and scores for the overall summary calculation
            category_counts[art_data['category']] = category_counts.get(art_data['category'], 0) + 1
            total_score += art_data['sentiment_score']

            # Run Named Entity Recognition (The heaviest NLP pipeline)
            entities = extract_entities(text_block)
            
            db_article = db.query(models.Article).filter(models.Article.url == art_data["url"]).first()
            if db_article:
                for entity in entities:
                    entity_text_cleaned = entity["text"].strip().title()
                    all_extracted_entities.append(entity_text_cleaned)
                    
                    new_entity = models.Entity(
                        article_id=db_article.id,
                        state=state,
                        entity_text=entity_text_cleaned,
                        entity_label=entity["label"]
                    )
                    db.add(new_entity)
        
        db.commit()

        # Compute Top Entities in-memory for the LLM
        scored_entities = []
        for art_data in analyzed_articles:
            entities = extract_entities(f"{art_data['title']} {art_data['summary']}")
            for entity in entities:
                scored_entities.append((entity["text"].strip().title(), entity["score"]))
  
        entity_totals = defaultdict(float)
        for name, score in scored_entities:
            entity_totals[name] += score
        top_5_counted = sorted(entity_totals.items(), key=lambda x: x[1], reverse=True)[:5]
        top_entities_str = ", ".join([item[0] for item in top_5_counted])
        headlines_str = "\n".join([f"- {a['title']}" for a in analyzed_articles[:5]])
        
        avg_score = (total_score / len(analyzed_articles) if analyzed_articles else 0)
        overall_sentiment = "positive" if avg_score > 0.1 else ("negative" if avg_score < -0.1 else "neutral")

        # Generate the costly LLM executive brief
        ai_insight = generate_ai_insight(
            state=state,
            overall_sentiment=overall_sentiment,
            top_category=max(category_counts, key=category_counts.get) if category_counts else "General",
            article_count=len(analyzed_articles),
            top_entities=top_entities_str,
            headlines=headlines_str
        )

        # Update or save the final state statistics record
        db.query(models.StateSummary).filter(models.StateSummary.state == state).delete()
        summary_entry = models.StateSummary(
            state=state,
            overall_sentiment=overall_sentiment,
            top_category=max(category_counts, key=category_counts.get) if category_counts else "General",
            article_count=len(analyzed_articles),
            sentiment_score=avg_score,
            ai_insights=ai_insight
        )
        db.add(summary_entry)
        db.commit()
        print(f"✅ Heavy NLP Background tasks completed for: {state}")

    except Exception as e:
        print(f"❌ Background pipeline failure: {str(e)}")
    finally:
        db.close()


@app.get("/news/{state}")
def get_news( state: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    existing_articles = db.query(models.Article).filter(models.Article.state == state).order_by(models.Article.published_at.desc()).all()

    if existing_articles:
        return [
            {
                "title": art.title,
                "url": art.url,
                "image": art.image,
                "publishedAt": art.published_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "summary": art.summary,
                "sentiment": [art.sentiment, art.sentiment_score],
                "sentiment_score": art.sentiment_score,
                "category": art.category
            }
            for art in existing_articles
        ]

    query = STATE_QUERIES.get(state, state)

    url = (f"https://newsapi.org/v2/everything?"f"q={query}&language=en&apiKey={API_key}")

    response = requests.get(url)
    data = response.json()

    if "articles" not in data:
        raise HTTPException(
            status_code=500,
            detail="Error fetching data from NewsAPI"
        )

    articles_to_return = []
    seen_urls = set()

    for article in data["articles"][:15]:

        article_url = article.get("url")

        if not article_url:
            continue

        # Skip duplicate URLs in same API response
        if article_url in seen_urls:
            continue

        seen_urls.add(article_url)

        # Skip if article already exists anywhere in DB
        existing_article = db.query(models.Article).filter(
            models.Article.url == article_url
        ).first()

        if existing_article:
            continue

        description = (
            article.get("description")
            or "No description available"
        )

        text_block = f"{article['title']} {description}"
        category = classify_category(text_block)
        sentiment = get_sentiment(text_block)

        new_article = models.Article(
            state=state,
            title=article["title"],
            summary=description,
            category=category,
            sentiment=sentiment[0],
            sentiment_score=sentiment[1],
            description=description,
            image=article.get("urlToImage"),
            url=article_url,
            published_at=datetime.strptime(article["publishedAt"], "%Y-%m-%dT%H:%M:%SZ")
        )

        db.add(new_article)

        articles_to_return.append({
            "title": article["title"],
            "url": article_url,
            "image": article.get("urlToImage"),
            "publishedAt": article["publishedAt"],
            "summary": description,
            "sentiment": sentiment,
            "sentiment_score": sentiment[1],
            "category": category
        })

    db.commit()

    if articles_to_return:
        background_tasks.add_task(process_heavy_ai_analytics, state, articles_to_return)
    
    return articles_to_return

@app.get("/state-summary")
def state_summary(db: Session = Depends(get_db)):
    return db.query(models.StateSummary).all()

@app.get("/analytics/{state}")
def get_analytics(state: str, db: Session = Depends(get_db)):
    
    # 1. State Summary
    summary = db.query(models.StateSummary)\
                .filter(models.StateSummary.state == state).first()

    # 2. Top Entities
    entities = db.query(
        models.Entity.entity_text,
        func.count(models.Entity.entity_text).label("count")
    ).filter(models.Entity.state == state)\
     .group_by(models.Entity.entity_text)\
     .order_by(func.count(models.Entity.entity_text).desc())\
     .limit(10).all()

    # 3. Category Distribution
    categories = db.query(
        models.Article.category,
        func.count(models.Article.category).label("count")
    ).filter(models.Article.state == state)\
     .group_by(models.Article.category)\
     .order_by(func.count(models.Article.category).desc()).all()

    # 4. Sentiment Distribution
    sentiments = db.query(
        models.Article.sentiment,
        func.count(models.Article.sentiment).label("count")
    ).filter(models.Article.state == state)\
     .group_by(models.Article.sentiment).all()

    # 5. Activity Trend
    activity = db.query(
        func.date(models.Article.published_at).label("date"),
        func.count(models.Article.id).label("count")
    ).filter(models.Article.state == state)\
     .group_by(func.date(models.Article.published_at))\
     .order_by(func.date(models.Article.published_at)).all()

    # 6. Sentiment Trend + Coverage Intensity (same query, compute both)
    trend_data = db.query(
        func.date(models.Article.published_at).label("date"),
        func.avg(models.Article.sentiment_score).label("avg_score"),
        func.count(models.Article.id).label("count")
    ).filter(models.Article.state == state)\
     .group_by(func.date(models.Article.published_at))\
     .order_by(func.date(models.Article.published_at)).all()

    # 7. News Freshness
    latest_article = db.query(models.Article)\
        .filter(models.Article.state == state)\
        .order_by(models.Article.published_at.desc())\
        .first()

    # 8. Alert Level (needs all articles)
    all_articles = db.query(models.Article)\
                     .filter(models.Article.state == state).all()

    # ── Compute derived metrics ──────────────────────────────

    # Sentiment Trend
    sentiment_trend = [
        {"date": str(t[0]), "score": round(t[1] or 0, 2)}
        for t in trend_data
    ]

    # Coverage Intensity
    counts = [t[2] for t in trend_data]
    if len(counts) >= 2:
        today_count = counts[-1]
        previous_days = counts[-8:-1] if len(counts) >= 8 else counts[:-1]
        avg_past = sum(previous_days) / len(previous_days)
        ratio = round(today_count / avg_past, 2) if avg_past > 0 else 1
        coverage = "High" if ratio > 1.5 else ("Low" if ratio < 0.5 else "Normal")
    else:
        ratio, coverage = 1, "Normal"

    # Sentiment Shift
    if len(trend_data) >= 2:
        today_score = trend_data[-1][1] or 0
        prev_score = trend_data[-2][1] or 0
        change = round(today_score - prev_score, 2)
        shift = "Positive" if change > 0.1 else ("Negative" if change < -0.1 else "Stable")
    else:
        change, shift = 0, "Stable"

    # Topic Diversity
    unique_cats = len(categories)
    diversity = "High" if unique_cats >= 5 else ("Medium" if unique_cats >= 3 else "Low")

    # News Freshness
    if latest_article:
        from datetime import timezone
        now = datetime.now(timezone.utc)
        hours_old = (now - latest_article.published_at.replace(tzinfo=timezone.utc))\
                    .total_seconds() / 3600
        freshness = "Very Fresh" if hours_old < 6 else \
                    "Fresh" if hours_old < 24 else \
                    "Moderate" if hours_old < 72 else "Stale"
        age = f"{round(hours_old/24, 1)} days" if hours_old > 36 \
              else f"{round(hours_old)} hours"
    else:
        freshness, age = "Unknown", None

    # Alert Level
    if all_articles:
        article_count = len(all_articles)
        neg_count = sum(1 for a in all_articles if a.sentiment == "negative")
        neg_ratio = neg_count / article_count
        avg_sent = sum(a.sentiment_score or 0 for a in all_articles) / article_count
        sentiment_risk = max(0, -avg_sent)
        volume_risk = min(article_count / 15, 1.0)
        alert_score = sentiment_risk * 0.5 + neg_ratio * 0.3 + volume_risk * 0.2
        alert_level = "Critical" if alert_score >= 0.75 else \
                      "High" if alert_score >= 0.55 else \
                      "Moderate" if alert_score >= 0.30 else "Low"
    else:
        alert_score, alert_level, neg_ratio, article_count = 0, "Unknown", 0, 0

    return {
        "summary": {
            "overall_sentiment": summary.overall_sentiment if summary else None,
            "top_category":      summary.top_category if summary else None,
            "article_count":     summary.article_count if summary else 0,
            "sentiment_score":   summary.sentiment_score if summary else 0,
            "ai_insights":       summary.ai_insights if summary else None
        },
        "entities":        [{"entity": e[0], "count": e[1]} for e in entities],
        "categories":      [{"category": c[0], "count": c[1]} for c in categories],
        "sentiments":      [{"sentiment": s[0], "count": s[1]} for s in sentiments],
        "activity_trend":  [{"date": str(t[0]), "count": t[2]} for t in trend_data],
        "sentiment_trend": sentiment_trend,
        "coverage": {
            "coverage": coverage,
            "ratio": ratio
        },
        "sentiment_shift": {
            "shift": shift,
            "change": change
        },
        "topic_diversity": {
            "diversity": diversity,
            "category_count": unique_cats
        },
        "news_freshness": {
            "freshness": freshness,
            "age": age
        },
        "alert_level": {
            "level": alert_level,
            "score": round(alert_score * 100, 1),
            "negative_ratio": round(neg_ratio * 100, 1),
            "article_count": article_count
        }
    }
# Quick endpoint to clear one state — add temporarily to main.py
@app.delete("/cache/{state}")
def clear_cache(state: str, db: Session = Depends(get_db)):
    db.query(models.Article).filter(models.Article.state == state).delete()
    db.query(models.StateSummary).filter(models.StateSummary.state == state).delete()
    db.query(models.Entity).filter(models.Entity.state == state).delete()
    db.commit()
    return {"status": f"Cleared {state}"}