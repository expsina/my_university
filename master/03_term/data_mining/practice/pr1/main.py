import pandas as pd

# pd.read_csv('datasets/csv/russian_news.csv').to_parquet(
#     path='datasets/parquet/russian_news.parquet',
#     engine='pyarrow',
#     compression='zstd',
#     index=False,
# )

print(pd.read_parquet(
    path='datasets/parquet/russian_news.parquet'
).head(10))
