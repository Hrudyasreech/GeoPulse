import os
import requests
from config.categories import category_keywords

HF_TOKEN = os.environ.get("HF_TOKEN")

def classify_category(text):
    text_lower = text.lower()

    category_scores = {category: 0 for category in category_keywords}

    for category, keywords in category_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                category_scores[category] += 1

    max_score = max(category_scores.values())

    # No keyword matched → use HF
    if max_score == 0:
        return classify_category_advanced(text)

    return max(category_scores, key=category_scores.get)


def classify_category_advanced(text):
    if not HF_TOKEN:
        print("HF_TOKEN not set")
        return "General"

    api_url = (
        "https://router.huggingface.co/"
        "hf-inference/models/facebook/bart-large-mnli"
    )

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}"
    }

    payload = {
        "inputs": text,
        "parameters": {
            "candidate_labels": list(category_keywords.keys())
        }
    }

    try:
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code != 200:
            print(f"HF Error: {response.status_code}")
            print(response.text)
            return "General"

        result = response.json()

        print("HF RESPONSE:", result)

        if not result:
            return "General"

        best_prediction = result[0]

        label = best_prediction["label"]
        score = best_prediction["score"]

        print(f"HF Prediction: {label} ({score:.3f})")

        if score < 0.30:
            print("Rejected by threshold")
            return "General"

        return label

    except requests.exceptions.Timeout:
        print("HF Timeout")
        return "General"

    except Exception as e:
        print(f"Category Classification Error: {e}")
        return "General"