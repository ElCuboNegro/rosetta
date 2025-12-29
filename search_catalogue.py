import pandas as pd
from pathlib import Path

csv_path = Path("data/01_raw/ben_yehuda_dump/pseudocatalogue.csv")
df = pd.read_csv(csv_path)

print(f"Total entries: {len(df)}")
print("Columns:", df.columns.tolist())

# Search for Shakespeare
shakespeare_matches = df[
    df["authors"].str.contains("שייקספיר", na=False)
    | df["authors"].str.contains("Shakespeare", na=False)
]
print("\nShakespeare matches:", len(shakespeare_matches))
print(shakespeare_matches[["ID", "path", "title", "authors"]].head(10).to_string())

# Search for Kafka
kafka_matches = df[
    df["authors"].str.contains("קפקא", na=False) | df["authors"].str.contains("Kafka", na=False)
]
print("\nKafka matches:", len(kafka_matches))
print(kafka_matches[["ID", "path", "title", "authors"]].head(10).to_string())

# Search for titles
titles = ["המשפט", "המלט", "אותלו", "דון קיחוטי", "דון קישוט"]
for title in titles:
    title_matches = df[df["title"].str.contains(title, na=False)]
    print(f"\nMatches for '{title}':", len(title_matches))
    print(title_matches[["ID", "path", "title", "authors"]].head(5).to_string())
