
      #TODO - update output of thematic analysis  
""" 
      #0 MESSAGE_ID, 1 MESSAGE_FULL_DATE, 2 MESSAGE_DATE_MONTH_DAY_YEAR, 3 MESSAGE_DATE_HOUR_SEC, 4 MESSAGE_FILE_NAME, 5 MESSAGE_SOURCE_LANGUAGE, 6 MESSAGE_DETECTED_LANGUAGE, 7 MESSAGE_TRANSLATED_ENG   
      MESSAGE_DOCUMENTATION_dict = {MESSAGE_DOCUMENTATION_FIELDS[0]: individual_message[ID], 
                                    MESSAGE_DOCUMENTATION_FIELDS[1]: individual_message[DATE_HUMAN], 
                                    MESSAGE_DOCUMENTATION_FIELDS[2]: message_dates[0], 
                                    MESSAGE_DOCUMENTATION_FIELDS[3]: message_dates[1], 
                                    MESSAGE_DOCUMENTATION_FIELDS[4]: message_file_name,
                                    MESSAGE_DOCUMENTATION_FIELDS[5]: message_text,
                                    MESSAGE_DOCUMENTATION_FIELDS[6]: ChatGPTOutput_Detected_Language,
                                    MESSAGE_DOCUMENTATION_FIELDS[7]: ChatGPTOutput_ENG_Translated_Message}

      with open(MESSAGE_DOCUMENTATION_FILE, 'a',newline='', encoding="utf-8") as f_object:
  
        # Pass the file object and a list
        # of column names to DictWriter()
        # You will get a object of DictWriter
        dictwriter_object = DictWriter(f_object, fieldnames=MESSAGE_DOCUMENTATION_FIELDS)
    
        # Pass the dictionary as an argument to the Writerow()
        dictwriter_object.writerow(MESSAGE_DOCUMENTATION_dict)
  
        # Close the file object
        f_object.close()
 """
