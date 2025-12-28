from src.rosetta_dict.pipelines.data_acquisition.nodes import download_benyehuda_data
import logging

logging.basicConfig(level=logging.INFO)


def test_full_scraper():
    print("Testing full scraper...")
    files = download_benyehuda_data(output_dir="data/01_raw", limit=2)
    print(f"Downloaded {len(files)} files.")
    for f in files:
        print(f" - {f}")


if __name__ == "__main__":
    test_full_scraper()
