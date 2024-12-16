#https://thepythoncode.com/article/bleu-score-in-python?utm_content=cmp-true
#https://www.nltk.org/_modules/nltk/translate/bleu_score.html

from nltk.translate.bleu_score import sentence_bleu, corpus_bleu
import csv
from csv import DictWriter

#open CSV file
DIR = "C:/Users/BrianT/RIT/RESEARCH/Fullbright_Poland/datasets/TG_Help_for_Ukrainians_in_Poland_Indivual_Messages/BLUE_eval/"
MESSAGE_DOCUMENTATION_FILE = "TG_messages_23_Jan_2024_BLUE_PROCESS.csv"
BLUE_SCORES_FILE = "BLUE_EVAL_SCORES.csv"

#FIELD NAMES
MESSAGE_ID = "MESSAGE_ID"
MACHINE_ENG = "MESSAGE_MACHINE_TRANSLATED_ENG"
HUMAN_ENG = "HUMAN_TRANSLATION_MESSAGE_ENG"
BLUE_SENTENCE_SCORE = "BLUE_SENTENCE_SCORE"

BLUE_EVAL_SENTENCE_FIELDS = [MESSAGE_ID, BLUE_SENTENCE_SCORE]


sentence_only = False

if sentence_only:

    #https://docs.python.org/3/library/csv.html
    sentence_result_list = []


    with open(DIR + MESSAGE_DOCUMENTATION_FILE, mode='r',newline='', encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            print(row[MESSAGE_ID],row[MACHINE_ENG], row[HUMAN_ENG])

            #split the MACHINE_EN
            machine_translation =  row[MACHINE_ENG].split()
            #split the HUMAN_EN
            human_translation =  row[HUMAN_ENG].split()

            # Calculate the BLEU score for a single sentence
            # The function calculates the BLEU score, which indicates the similarity between the candidate and reference sentences:
            #,(0.5,0.5)
            #bleu_score = sentence_bleu([human_translation], machine_translation)

            # Calculate BLEU score with 2-gram weight
            # This will calculate the BLEU score with equal weights assigned to 1-gram and 2-gram precision (0.5 for each). 
            #bleu_score = sentence_bleu([human_translation], machine_translation, weights=(0.5, 0.5))


            # Calculate BLEU score with four n-gram weight
            #In this example, each n-gram weight is set to 0.25, indicating equal weighting for 1-gram, 2-gram, 3-gram, and 4-gram precision. 
            bleu_score = sentence_bleu([human_translation], machine_translation, weights=(0.1, 0.1, 0.4, 0.4))




            temp_list = [row[MESSAGE_ID],bleu_score]
            sentence_result_list.append(temp_list)

            print("BLEU Score: ", bleu_score)   


        
    
        # Close the file object
        csvfile.close()



    #document the sentence score in a CSV file
    with open(DIR + BLUE_SCORES_FILE, 'a',newline='', encoding="utf-8") as f_object:
    
        # Pass the file object and a list of column names to DictWriter()
        # You will get a object of DictWriter
        dictwriter_object = DictWriter(f_object, fieldnames=BLUE_EVAL_SENTENCE_FIELDS)


        #loop through the sentence eval results
        # Pass the dictionary as an argument to the Writerow()

        for result in sentence_result_list:

            BLUE_EVAL_SENTENCE_dict = {BLUE_EVAL_SENTENCE_FIELDS[0]: result[0], 
                                    BLUE_EVAL_SENTENCE_FIELDS[1]: result[1]}
            dictwriter_object.writerow(BLUE_EVAL_SENTENCE_dict)

        # Close the file object
        f_object.close()


#***** Corpus evaluation **** 
references = []
translations = []


with open(DIR + MESSAGE_DOCUMENTATION_FILE, mode='r',newline='', encoding="utf-8-sig") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        print(row[MESSAGE_ID],row[MACHINE_ENG], row[HUMAN_ENG])

        #split the MACHINE_EN
        machine_translation =  row[MACHINE_ENG].split()
        translations.append(machine_translation)

        #split the HUMAN_EN
        human_translation =  row[HUMAN_ENG].split()
        references.append(human_translation)
    
    # Close the file object
    csvfile.close()


# Prepare the reference sentences and candidate sentences for multiple translations
#references = [['I', 'love', 'eating', 'ice', 'cream'], ['He', 'enjoys', 'eating', 'cake']]




#translations = [['I', 'love', 'eating', 'ice', 'cream'], ['He', 'likes', 'to', 'eat', 'cake']]
 
# Create a list of reference lists
references_list = [[ref] for ref in references]

#weights=(0.1, 0.1, 0.4, 0.4) 
# Calculate BLEU score for the entire corpus
bleu_score_corpus = corpus_bleu(references_list, translations,weights=(0.25, 0.25,0.25,0.25) ) 
print("Corpus BLEU Score: ", bleu_score_corpus)

