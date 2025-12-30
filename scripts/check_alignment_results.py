import pandas as pd
from pathlib import Path


def check_results():
    file_path = Path("data/02_intermediate/aligned_books.parquet")
    if not file_path.exists():
        print("File not found.")
        return

    try:
        df = pd.read_parquet(file_path)
        print(f"Total aligned sentences: {len(df)}")

        books = df["source_book"].unique()
        print(f"Books aligned: {len(books)}")
        for book in books[:10]:
            print(f" - {book}")

        quijote_books = [b for b in books if "Quijote" in b]
        if quijote_books:
            print(f"✅ Quijote alignments found in: {quijote_books}")
            print(f"Count: {len(df[df['source_book'].isin(quijote_books)])}")
        else:
            print("❌ Quijote not found in aligned books.")

        history_books = [b for b in books if "Historia" in b or "Judíos" in b]
        if history_books:
            print(f"✅ History books found: {history_books}")
            print(f"Count: {len(df[df['source_book'].isin(history_books)])}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    check_results()
