from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from database import Base

class Article(Base):
    __tablename__ = "articles"
    id = Column(Integer, primary_key=True, index=True)
    state = Column(String, index=True)
    title = Column(String, index=True)  
    summary = Column(String)
    category = Column(String)
    sentiment = Column(String)
    sentiment_score = Column(Float)
    description = Column(String)
    image = Column(String)
    url = Column(String, unique=True, index=True)
    published_at = Column(DateTime)

class StateSummary(Base):
    __tablename__ = "state_summary"
    id = Column(Integer, primary_key=True, index=True)
    state = Column(String, unique=True, index=True)
    overall_sentiment = Column(String)
    top_category = Column(String)
    article_count = Column(Integer)
    sentiment_score = Column(Float)
    ai_insights = Column(String)

class Entity(Base):
    __tablename__ = "entities"
    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"))
    state = Column(String, index=True)
    entity_text = Column(String)
    entity_label = Column(String)
