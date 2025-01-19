import json
from aiLoader import loadAI

client = loadAI()

keywordsDict = {
    "Legal Status and Documentation" : "temporary protection, residence permit, ID card, TIN, passport",
    "Safety and Security" : "discrimination, harassment, physical attack, safety, security",
    "Gender-Based Violence" : "domestic violence, sexual harassment, inappropriate behavior, hotline",
    "Employment" : "job search, employment opportunities, hiring, unemployment, work permit",
    "Polish Language Proficiency" : "Polish classes, language barrier, communication, translator",
    "Livelihood Coping Strategies" : "saving money, selling belongings, taking high-risk jobs, cutting expenses",
    "Living Arrangements" : "apartment, shared housing, host family, collective site",
    "Living Conditions" : "privacy issues, no hot water, transportation problems, overcrowding",
    "Pressure to Leave Accommodation" : "eviction, landlord issues, rent increase, can't pay rent",
    "School Enrollment" : "school registration, Polish school, Ukrainian school, online classes",
    "Barriers to Education" : "language barrier, waiting list, lack of documents, cultural difference",
    "Remote Learning" : "online learning, remote classes, platform access, teacher supervision",
    "Access to Healthcare" : "doctor appointment, healthcare access, medical checkup, clinic visit",
    "Mental Health Support" : "mental health support, counseling, therapy, emotional well-being",
    "Barriers to MHPSS" : "stigma, awareness issue, confidentiality concerns, privacy",
    "Negative Attitudes from Host Communities" : "verbal abuse, aggression, hate speech, unfriendly behavior",
    "Perceived Reasons for Hostility" : "language difference, nationality, economic reasons, cultural clash",
    "Social Media Hostility" : "online comments, hate speech, xenophobia, discrimination",
    "Aid Received" : "social benefits, cash assistance, food aid, rental support",
    "Information Needs" : "helpline, information center, government office, assistance",
    "Feedback and Reporting" : "feedback form, complaint, suggestion box, report issue",
    "Future Intentions" : "stay in Poland, return to Ukraine, move to another country, undecided",
    "Visits to Ukraine" : "visit family, collect documents, short trip, border crossing",
    "Challenges Returning to Poland" : "lost protection status, visa issues, re-entry problem, waiting time"
}

jsonFile = "C:/Users/Olivia Croteau/Documents/GitHub/fulbright_research/production/processedJson/9Ukraine - Помощь в КраковеTranslated.json"

# Prompts
PROMPT_PART_1 = "Conduct a thematic analysis of this text <start> " 
PROMPT_PART_2 = " <end>. Return back two things."

PROMPT_PART_3 = "The first is your general thematic assesment of text that was between the <start> and <end> tags. The second are any subtopics that the text between the <start> and <end> tags may belong to. The text can belong to one, many, or no subtopics. The subtopics are listed out as keys in this dictionary between the <dict> tags, the value for each key contains keywords that you may use to sort the text into subtopics. <dict>"

PROMPT_PART_4 = " <dict> Put the two items you return into a JSON structure. Your general thematic assesment of text that was between the <start> and <end> tags placed inside a JSON tag named theme. Any topics you found in the text that was between the <start> and <end> tags inside a JSON tag named topic."

PROMPT_PART_5 = "Do not return any additional text, descriptions of your process or information beyond two items and output format of the tags specified. Do not encapsulate the result in ``` or any other characters."

MOTIVATION_MESSAGE = "You are a skilled humanitarian analyst who is an expert in conducting thematic analysis of English language texts."

def thematize(text):
    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            store=True,
            messages=[
                {"role": "system", "content": MOTIVATION_MESSAGE},
                {"role": "user", "content": PROMPT_PART_1 + text + PROMPT_PART_2 + PROMPT_PART_3 + str(keywordsDict) + PROMPT_PART_4 + PROMPT_PART_5}
            ]
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error summarizing text: {e}")
        return None


# start with just text_entity translations
with open(jsonFile, 'r', encoding='utf-8') as f:
    jsonData = json.load(f)
    messageData = jsonData.get("messages", []) # Create array of message data

    for message in messageData:
        textEntities = message.get("text_entities", [])

        fullText = ""

        for entity in textEntities:
            if "TRANSLATED_TEXT" in entity:
                fullText += entity["TRANSLATED_TEXT"]

        if fullText:
            print(f"FULLTEXT {message.get("id")}: {fullText}")
            analysis = thematize(fullText)
            print(analysis)
            print("*******")