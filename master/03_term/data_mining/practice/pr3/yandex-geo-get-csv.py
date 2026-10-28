# %%
from datasets import load_dataset
import pandas as pd

dataset = load_dataset(
    "d0rj/geo-reviews-dataset-2023",
    split="train"
)
df = pd.DataFrame(dataset)


# %%
df.to_csv('yandex-geo.csv')


