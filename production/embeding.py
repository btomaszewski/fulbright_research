import json
from sentence_transformers import SentenceTransformer, util

categories = ["Legal Status and Documentation", "Safety and Security", "Gender-Based Violence", "Employment", "Challenges Returning to Poland", "Visits to Ukraine", "Future Intentions", "Feedback and Reporting", "Information Needs", "Aid Received", "Social Media Hostility", "Polish Language Proficiency",
    "Livelihood Coping Strategies", 
    "Living Arrangements",
    "Living Conditions",
    "Pressure to Leave Accommodation",
    "School Enrollment",
    "Barriers to Education",
    "Remote Learning",
    "Access to Healthcare",
    "Mental Health Support",
    "Barriers to MHPSS",
    "Negative Attitudes from Host Communities",
    "Perceived Reasons for Hostility"]

model = SentenceTransformer('all-mpnet-base-v2')
category_embeddings = model.encode(categories) 

def category_sim_pairs(categories, similarities):
    output = []
    for index in range(len(categories)):
        output.append( (categories[index], similarities[index]) )

    output = sorted(output, key=lambda x: x[1], reverse=True)
    return output

with open('testembed.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for messages in data:
    id = messages.get("id")
    text = messages.get("TRANSLATION", '')
    translation = messages.get("TRANSLATION", {})
    translated_text = translation.get("Translated_Text", '')

    # description -> vector
    text_embedding = model.encode(text)

    # cosine sim (description, category)
    similarities = util.cos_sim(text_embedding, category_embeddings)[0].tolist()
    pairs = category_sim_pairs(categories, similarities)

    print(f"Title: {id}:")
    print(f"  Description: {text}")
    print(f"  Categories (closest to furthest):")
    for category, similarity in pairs:
        print(f"{category}: {similarity:.4f}")
    print("#"*30)
