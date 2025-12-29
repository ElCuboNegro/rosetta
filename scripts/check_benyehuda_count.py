import requests
from bs4 import BeautifulSoup


def check_count():
    base_url = "https://benyehuda.org/authors"

    resp = requests.get(base_url)
    soup = BeautifulSoup(resp.text, "html.parser")
    links = soup.select("a[href^='https://benyehuda.org/author/']")
    if not links:
        links = soup.select("a[href^='/author/']")

    print(f"Author links count: {len(links)}")
    if links:
        print(f"First Author: {links[0].get_text(strip=True)}")

    # Inspect Alphabet Links specifically on /authors
    for char in ["א", "ב", "ג", "A", "B"]:  # checking Latin too?
        link = soup.find("a", string=char)
        if link:
            print(f"Link for {char}: '{link.get('href')}'")
        else:
            print(f"No link found for {char}")


if __name__ == "__main__":
    check_count()
