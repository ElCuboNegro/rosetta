import requests
import json
import re


def search_gutenberg(query, language=None):
    """Search Gutenberg using Gutendex API."""
    url = "https://gutendex.com/books"
    params = {"search": query}
    if language:
        params["languages"] = language

    print(f"Searching: {query} (Language: {language})")
    try:
        resp = requests.get(url, params=params)
        data = resp.json()

        if data["count"] > 0:
            print(f"Found {data['count']} matches.")
            for book in data["results"][:3]:
                print(
                    f" - {book['title']} by {book['authors'][0]['name'] if book['authors'] else 'Unknown'} (ID: {book['id']})"
                )
                print(f"   Languages: {book['languages']}")
        else:
            print("No matches found.")

    except Exception as e:
        print(f"Error: {e}")


# Sample Data (simulating extraction from Ben Yehuda)
# Ben Yehuda ID 60371 is "Hierosolyma est Perdita" by Deborah Amir (Modern poem, unlikely in Gutenberg)
# Let's try a classic: Don Quixote
samples = [
    {"original_title": "Don Quixote", "author": "Cervantes"},
    {"original_title": "Hamlet", "author": "Shakespeare"},
    {"original_title": "The Trial", "author": "Kafka"},  # Der Process
]

print("--- Testing Gutendex API ---")
for s in samples:
    search_gutenberg(s["original_title"], "en")
    search_gutenberg(s["original_title"], "es")
