import requests
import json


def check_lang(lang):
    url = f"https://gutendex.com/books?languages={lang}&sort=popular"
    print(f"Querying: {url}")
    try:
        resp = requests.get(url)
        data = resp.json()
        print(f"Count for {lang}: {data.get('count')}")
        results = data.get("results", [])[:5]
        for book in results:
            print(f"Title: {book.get('title')}")
            print(f"Formats: {list(book.get('formats', {}).keys())}")
    except Exception as e:
        print(f"Error: {e}")


print("--- SPANISH ---")
check_lang("es")
print("\n--- HEBREW ---")
check_lang("he")
