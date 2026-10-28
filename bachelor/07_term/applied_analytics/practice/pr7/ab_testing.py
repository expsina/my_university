# %%
import pandas as pd

tres = pd.read_csv("AB_Test_Results.csv")
tres.columns = ["user_id", "var_name", "rev"]

tres.head()

# %%
tres.shape

# %%
tres.isna().sum()

# %%
len(tres["user_id"].unique())

# %%
tres.dtypes

# %%
tres.groupby(by = ["user_id", "var_name"]).sum()

# %%
arr = tres.to_numpy()
double_users = []

for i in arr:

    for j in arr:

        if i[0] == j[0]:

            if i[1] != j[1]:
                double_users.append(i[0])
                break

double_users

# %%
mask = tres["user_id"].isin(double_users)

# %%
cl_tres = tres.loc[~mask]

# %%
cl_tres.shape

# %%
cl_tres.sort_values(by = ["user_id"], ascending = True)

# %%
dd_cl_tres = cl_tres.drop_duplicates(subset = ["user_id"])

# %%
dd_cl_tres = dd_cl_tres[dd_cl_tres["rev"] > 0]

# %%
dd_cl_tres.shape

# %%
dd_cl_tres.dtypes

# %%
import matplotlib.pyplot as plt

dd_cl_tres.boxplot(by = ["var_name"], column = ["rev"])
plt.show()

# %%
rev_q1 = dd_cl_tres["rev"].quantile(0.25)
rev_q3 = dd_cl_tres["rev"].quantile(0.75)
rev_iqr = rev_q3 - rev_q1

dd_cl_tres = dd_cl_tres[(dd_cl_tres["rev"] <= rev_q3 + 1.5 * rev_iqr) & (dd_cl_tres["rev"] > rev_q1 - 1.5 * rev_iqr)]

# %%
rev_q3 - 1.5 * rev_iqr

# %%
plt.clf()

# %%
dd_cl_tres.boxplot(column = ["rev"], by = "var_name")
plt.show()

# %%
dd_cl_tres.shape

# %%
dd_cl_tres.sort_values(by = "rev", ascending = True)

# %%
dd_cl_tres.groupby(by = "var_name").count()

# %%



