#read XLSX, convert to csv
import pandas as pd
import csv
import gc

PESEL_CSV = "PESEL.csv"
FINAL_PESEL_CSV = "final_pesel.csv"

#fields
fields = ["ID","TERYT",	"POWIAT",
        "WOJEWÓDZTWO",	"KOBIET_total",
         "MĘŻCZYZN_total",	"WSZYSTKICH_total",	
         "m_2023",	"m_2022",	"m_2021",	"m_2020",
         "m_2019",	"m_2018",	"m_2017","m_2016",
         "m_2015","m_2014",	"m_2013","m_2012",
         "m_2011","m_2010",	"m_2009","m_2008",	
         "m_2007",	"m_2006","m_2005","m_2004",
         "m_1999-2003","m_1994-1998","m_1989-1993","m_1984-1988",
         "m_1979-1983",	"m_1974-1978","m_1969-1973","m_1964-1968",
         "m_1959-1963",	"m_1958","k_2023","k_2022",	"k_2021","k_2020",
         "k_2019","k_2018",	"k_2017","k_2016","k_2015",	"k_2014",
         "k_2013","k_2012",	"k_2011","k_2010","k_2009",	"k_2008",	
         "k_2007","k_2006","k_2005","k_2004","k_1999-2003",	
         "k_1994-1998","k_1989-1993","k_1984-1988",	"k_1979-1983",
         "k_1974-1978",	"k_1969-1973","k_1964-1968","k_1959-1963",
          "k_1958"]


CSV_header = ",".join(fields)

#write out file with the header - new file
outputfile = open(FINAL_PESEL_CSV, "w", encoding="utf8")
outputfile.write(",".join(fields) + "\n")
outputfile.close()

#https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html
df = pd.read_excel('PESEL_10_Oct_2023.xlsx')

#export to CSV, easier to process
#https://docs.python.org/3/library/csv.html
df.to_csv(PESEL_CSV)

#modify if start of actual data changes
start_row = 3

with open (PESEL_CSV, encoding="utf8") as csvfile:
    peselreader = csv.reader(csvfile, delimiter=',')
    x = 0
    for row in peselreader:
        
        #actual data is found starting on row 4 (index 3)
        #write CSV header
        #loop row content into new structure with revised CSV header

        if x >= start_row:
            #put the row into the CSV 
        

            #having memory errors doing large string concats
            #write new records directly to the file
            outputfile = open(FINAL_PESEL_CSV, "a", encoding="utf8")
            outputfile.write(",".join(row) + "\n")
            outputfile.close()

        x += 1

print ("done")


