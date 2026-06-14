from preprocessing import clean_text_simple
from collections import Counter
import spacy

nlp = spacy.load("en_core_web_sm")
allowed_labels = {"PERSON", "ORG", "GPE"}
blocked = {
    "india","news","today","state","states", "government","breaking","reuters", "bbc","cnn","google","youtube","twitter","instagram","media","update"
}
label_weights = {
    "ORG": 2,
    "GPE": 2,
    "PERSON": 1
}

def extract_entities(text):

    cleaned_text = clean_text_simple(text)
    doc = nlp(cleaned_text)
    entity_counts = Counter()
    entity_labels = {}

    for ent in doc.ents:

        normalized = ent.text.strip().lower()
        if (
            ent.label_ in allowed_labels
            and len(normalized) > 3
            and normalized.isascii()
            and normalized not in blocked
        ):
            entity_counts[normalized] += 1
            entity_labels[normalized] = ent.label_

    ranked_entities = []

    for entity, count in entity_counts.items():

        label = entity_labels[entity]
        weight = label_weights.get(label, 1)
        score = count * weight
        ranked_entities.append({
            "text": entity.title(),
            "label": label,
            "count": count,
            "score": score
        })

    ranked_entities = sorted(
        ranked_entities,
        key=lambda x: x["score"],
        reverse=True
    )

    return ranked_entities[:10]