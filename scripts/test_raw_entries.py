import pandas as pd
import numpy as np

df = pd.read_parquet('data/02_intermediate/raw_spanish_entries.parquet')
print(f'Total rows: {len(df)}')
print('Columns:', df.columns.tolist())
print('\nSample row:')
for col in df.columns[:5]:  # Just first 5 columns
    val = df[col].iloc[0]
    print(f'{col}: {type(val).__name__} = {val if not isinstance(val, np.ndarray) else f"array({len(val)} items)"}')
