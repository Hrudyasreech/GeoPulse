from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer        

analyzer = SentimentIntensityAnalyzer()

def get_sentiment(text):

    if not text:
        return 'neutral'
    scores = analyzer.polarity_scores(text)
    compound_score = scores['compound']

    if compound_score >= 0.15:
        return 'positive', compound_score
    elif compound_score <= -0.15:
        return 'negative', compound_score
    else:
        return 'neutral', compound_score