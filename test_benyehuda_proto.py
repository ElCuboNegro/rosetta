import requests
from bs4 import BeautifulSoup


def test_download():
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
    )

    # 1. Visit the page to get the token
    url = "https://benyehuda.org/read/60049"
    print(f"visiting {url}...")
    response = session.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Try to find the token
    # The user/browser tool mentioned a form with action containing 'download'
    # We need the 'authenticity_token' input value
    token = None
    form = soup.find("form", action=lambda x: x and "download" in x)
    if form:
        token_input = form.find("input", {"name": "authenticity_token"})
        if token_input:
            token = token_input.get("value")
            print(f"Found token: {token[:20]}...")
        else:
            print("Form found but no authenticity_token input.")
            # print(form)

    if not token:
        print("Could not find token via form inspection. Searching all inputs...")
        token_input = soup.find("input", {"name": "authenticity_token"})
        if token_input:
            token = token_input.get("value")
            print(f"Found token via global search: {token[:20]}...")

    if not token:
        print("FAILED to find token.")
        return

    # 2. POST to download
    # The action might be absolute or relative. Browser tool said https://benyehuda.org/download/60049
    download_url = f"https://benyehuda.org/download/60049"
    payload = {
        "authenticity_token": token,
        "format": "txt",
        "commit": "הורדה",  # Using a generic value or what form suggests, often not strictly checked but good to have
    }

    print(f"Posting to {download_url}...")
    dl_response = session.post(download_url, data=payload)

    if dl_response.status_code == 200:
        print("Download successful!")
        print(f"Content-Type: {dl_response.headers.get('Content-Type')}")
        print(f"Content Length: {len(dl_response.text)}")
        print("Snippet:")
        print(dl_response.text[:200])
    else:
        print(f"Download failed: {dl_response.status_code}")
        print(dl_response.text[:500])


if __name__ == "__main__":
    test_download()
