import requests


def check_hebrew_formats():
    url = "https://gutendex.com/books?languages=he&sort=popular"
    try:
        data = requests.get(url).json()
        print(f"Total Hebrew Books: {data['count']}")
        for book in data["results"][:5]:
            print(f"\nTitle: {book['title']}")
            print("Formats:")
            for k, v in book["formats"].items():
                print(f"  - {k}")
    except Exception as e:
        print(e)


check_hebrew_formats()
