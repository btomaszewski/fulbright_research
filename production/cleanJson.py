import json
import shutil

file = "C:/Users/Olivia Croteau/Documents/GitHub/fulbright_research/testCode&Data/data/cleanJsonTestChat/result.json"

cleanFile = "C:/Users/Olivia Croteau/Documents/GitHub/fulbright_research/testCode&Data/data/cleanJsonTestChat/cleanResult.json"

shutil.copy(file, cleanFile)

messageData = []

with open(cleanFile, 'r', encoding='utf-8') as f:
    jsonData = json.load(f)
    messageData = jsonData.get("messages", []) # Create array of message data


# get rid of /nn
# make our own message ids/reply ids
# combine textEntities
# get rid of text




# Write messages to destination file
with open(cleanFile, 'w', encoding='utf-8') as f:
    json.dump(jsonData, f, ensure_ascii=False, indent=4)

