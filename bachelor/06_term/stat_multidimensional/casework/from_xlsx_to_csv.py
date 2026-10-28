import pandas as pd 

df = pd.read_csv('bachelor/5_term/stat_multidimensional/casework/case_data.csv', encoding='utf-8', sep='\t')
print(df.head())