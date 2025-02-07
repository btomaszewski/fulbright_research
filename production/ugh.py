import json

file = "C:/Users/Olivia Croteau/Documents/GitHub/fulbright_research/production/processedJson/Medyka-Shehyni_Feb-05-2025Processed/result.json"

with open(file, 'r', encoding='utf-8') as f:
    jsonData = json.load(f)
    messageData = jsonData.get("messages", [])

for message in messageData:
    if message.get('date'):
        date = message['date']
        date = date[:10]
        message['date'] = date

with open(file, 'w', encoding='utf-8') as f:
    json.dump(jsonData, f, ensure_ascii=False, indent=4)