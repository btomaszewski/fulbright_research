

from nltk.translate.bleu_score import sentence_bleu, corpus_bleu
import csv
from csv import DictWriter

#open CSV file
DIR = "C:/Users/BrianT/RIT/RESEARCH/Fullbright_Poland/datasets/TG_Help_for_Ukrainians_in_Poland_Indivual_Messages/BLUE_eval/"
MESSAGE_DOCUMENTATION_FILE = "TG_messages_14_Feb_2024_BLUE_EVAL_FULL_two_humans_MOD.csv"
BLUE_SCORES_FILE = "BLUE_EVAL_SCORES.csv"

#FIELD NAMES
MESSAGE_ID = "MESSAGE_ID"
MACHINE_ENG = "MESSAGE_MACHINE_TRANSLATED_ENG"
HUMAN_ENG_1 = "HUMAN_TRANSLATION_MESSAGE_ENG_1"
HUMAN_ENG_2 = "HUMAN_TRANSLATION_MESSAGE_ENG_2"



#***** Corpus evaluation **** 
references = []
translations = []


with open(DIR + MESSAGE_DOCUMENTATION_FILE, mode='r',newline='', encoding="utf-8-sig") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        print(row[MESSAGE_ID],row[MACHINE_ENG], row[HUMAN_ENG_1], row[HUMAN_ENG_2])

        #split the MACHINE_EN
        machine_translation =  row[MACHINE_ENG].split()
        translations.append(machine_translation)

        #split the HUMAN_EN
        
        human_translation_1 =  row[HUMAN_ENG_1].split()
        human_translation_2 =  row[HUMAN_ENG_2].split()
        references.append([human_translation_1, human_translation_2])

# Prepare the reference sentences and candidate sentences for multiple translations
#references = [['I', 'love', 'eating', 'ice', 'cream'], ['He', 'enjoys', 'eating', 'cake']]

#translations = [['I', 'love', 'eating', 'ice', 'cream'], ['He', 'likes', 'to', 'eat', 'cake']]
 

#weights=(0.1, 0.1, 0.4, 0.4) 
# Calculate BLEU score for the entire corpus
bleu_score_corpus = corpus_bleu(references, translations,weights=(0.1, 0.1, 0.4, 0.4) ) 
print("Corpus BLEU Score: ", bleu_score_corpus)

