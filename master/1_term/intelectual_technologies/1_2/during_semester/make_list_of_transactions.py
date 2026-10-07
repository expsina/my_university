from random import randint 
import pandas as pd 
import numpy as np 
import itertools

tuple_products = ("кефир", "молоко", "йогурт", "сметана", "сыр", "майонез", "яйца", "пиво", "мука", "блины", "творог",
                  "бананы", "кетчуп", "вода", "морковка", "капуста", "баклажан")
ls_transactions = [] 

for _ in range(20):
    len_transaction = randint(4, 6)
    transaction = []
    ls_indexes = []

    while True:
        rand_index = randint(0, 16)

        if rand_index not in ls_indexes:
            transaction.append(tuple_products[rand_index])
            ls_indexes.append(rand_index)

        if len(transaction) == len_transaction:
            ls_transactions.append(transaction)
            break

pd.DataFrame(ls_transactions).to_excel("1_2/transactions.xlsx", index = False)

# comb_3 = list(itertools.combinations(tuple_products, 3))

# print(pd.DataFrame(comb_3))
