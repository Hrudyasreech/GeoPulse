import google.generativeai as genai

genai.configure(api_key="AIzaSyAkjJ8Xzd6na79Ro5PHkJmsNfU4OSBoPVg")
model = genai.GenerativeModel('gemini-2.5-flash')

def generate_ai_insight(state: str, overall_sentiment: str, top_category: str, 
                         article_count: int, top_entities: str, headlines: str) -> str:
    prompt = f"""
You are a regional news intelligence analyst for GeoPulse.
State: {state}
Overall Sentiment: {overall_sentiment}
Top Category: {top_category}
Articles Analysed: {article_count}
Top Entities: {top_entities}
Key Headlines:
{headlines}
Write a 3-4 sentence intelligence brief. Connect the recurring themes, 
dominant entities, and sentiment patterns into a coherent narrative. 
Do NOT just list the statistics. Write like an analyst, not a bot.
"""
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return "AI insight could not be generated at this time."