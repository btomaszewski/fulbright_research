import json

file = "C:/Users/Olivia Croteau/AppData/Roaming/electron/processing/processedJson/Medyka-Shehyni_Jan_1-29/result.json";

newFile = "C:/Users/Olivia Croteau/Desktop/translations.txt"

with open(file, 'r', encoding='utf-8') as f:
    jsonData = json.load(f)
    messageData = jsonData.get("messages", [])

ids = []
texts = []
lang = []
trans = []

for message in messageData:
    if message.get('TRANSLATION'):
        ids.append(message['id'])
        texts.append(message['text'])
        lang.append(message['TRANSLATION']['language'])
        trans.append(message['TRANSLATION']['translation'])

with open(newFile, 'w', encoding='utf-8') as f:
    for id in ids:
        i = ids.index(id)
        
        f.write(f"{str(id)}\n")
        f.write(f"{texts[i]}\n")
        f.write(f"{lang[i]}\n")
        f.write(f"{str(trans[i])}\n")
        f.write("score:\n")
        f.write("notes:\n")
        f.write("\n")

    