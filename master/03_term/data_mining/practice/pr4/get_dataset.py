import hashlib
import pandas as pd
from datasets import load_dataset

df = load_dataset("d0rj/geo-reviews-dataset-2023", split="train").to_pandas()
print(len(df), df["rating"].value_counts().sort_index().to_dict())

# 1. Только оценки 1-5 (рейтинг 0 исключаем) и непустой текст
df = df[df["rating"].between(1, 5) & df["text"].notna()].copy()

# 2. Тональность из рейтинга
df["label"] = df["rating"].map({1: "negative", 2: "negative", 3: "neutral",
                                4: "positive", 5: "positive"})

# 3. Чистка: пробелы и «утёкшие» оценки в тексте
leak = r"\b\d{1,2}\s*(?:/|из)\s*(?:5|10)\b|\b\d{1,2}\s*(?:баллов?|звёзд\w*|звезд\w*)\b|\b\d\s*\*"
df["text"] = (df["text"].str.replace(leak, " ", regex=True)
                        .str.replace(r"\s+", " ", regex=True)
                        .str.strip().str.slice(0, 1000))
df = df[df["text"].str.len() >= 20]

# 4. Точные дубли (без регистра, знаков и пробелов)
key = df["text"].str.lower().str.replace(r"[^\w]+", "", regex=True)
df = df[~key.duplicated()]

# 5. Разбиение 70/30 ПО ОРГАНИЗАЦИЯМ: тест содержит организации, которых нет в обучении
org = df["name_ru"].fillna("") + "|" + df["address"].fillna("")
is_test = org.map(lambda s: int(hashlib.md5(s.encode()).hexdigest(), 16) % 10 < 3)
df["set"] = is_test.map({True: "test", False: "train"})

# 6. Баланс классов внутри каждой части
def balanced(part, n):
    n = min(n, part["label"].value_counts().min())
    return part.groupby("label").sample(n=n, random_state=42)

N_TRAIN, N_TEST = 1500, 500
train = balanced(df[df["set"] == "train"], N_TRAIN).sample(frac=1, random_state=1)
test = balanced(df[df["set"] == "test"], N_TEST).sample(frac=1, random_state=1)

cols = ["name_ru", "rubrics", "rating", "text", "label", "set"]
train[cols].to_csv("geo_train.csv", index=False, encoding="utf-8")
test[cols].to_csv("geo_test.csv", index=False, encoding="utf-8")
pd.concat([train, test])[cols].to_csv("geo_sent.csv", index=False, encoding="utf-8")
print(train["label"].value_counts().to_dict(), test["label"].value_counts().to_dict())
