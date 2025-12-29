import requests
import json
import time
from bs4 import BeautifulSoup
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_benyehuda_work(work_id: str, output_dir: str):
    base_url = "https://benyehuda.org"
    work_url = f"{base_url}/read/{work_id}"
    output_path = Path(output_dir) / f"{work_id}.json"

    logger.info(f"Downloading work {work_id} from {work_url}")

    session = requests.Session()
    session.headers.update({"User-Agent": "RosettaDictBot/1.0"})

    try:
        # 1. Get work page
        resp = session.get(work_url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        title = soup.title.string if soup.title else "Unknown"
        logger.info(f"Title: {title}")

        metadata_entries = []
        for meta in soup.select(".metadata"):
            text = meta.get_text(strip=True)
            if text:
                metadata_entries.append(text)

        # 2. Extract Token
        token = None
        form = soup.find("form", action=lambda x: x and "download" in x)
        if form:
            token_input = form.find("input", {"name": "authenticity_token"})
            if token_input:
                token = token_input["value"]

        if not token:
            # Try generic search
            token_input = soup.find("input", {"name": "authenticity_token"})
            if token_input:
                token = token_input["value"]

        if not token:
            logger.error("No authenticity_token found.")
            return

        # 3. Download Text
        download_url = f"{base_url}/download/{work_id}"
        payload = {"authenticity_token": token, "format": "txt", "commit": "הורדה"}

        dl_resp = session.post(download_url, data=payload)
        dl_resp.encoding = "utf-8"

        content = ""
        if dl_resp.status_code == 200:
            content = dl_resp.text
        else:
            logger.error(f"Download failed: {dl_resp.status_code}")
            return

        data = {
            "id": work_id,
            "url": work_url,
            "title": title,
            "content": content,
            "metadata": {"scraped_at": time.time(), "raw_metadata": metadata_entries},
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved to {output_path}")

    except Exception as e:
        logger.error(f"Error: {e}")


if __name__ == "__main__":
    download_benyehuda_work("11229", "data/01_raw/ben_yehuda")
