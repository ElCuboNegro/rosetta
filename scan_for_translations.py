import json


def scan_for_key(path, key, limit_mb=100):
    print(f"--- Scanning {path} for key '{key}' ---")
    chunk_size = 1024 * 1024  # 1MB
    bytes_read = 0
    found_count = 0

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                bytes_read += len(line.encode("utf-8"))
                if bytes_read > limit_mb * 1024 * 1024:
                    print(f"Scanned {limit_mb}MB limit. Stopping.")
                    break

                if f'"{key}"' in line:
                    try:
                        entry = json.loads(line)
                        # Check strictly for the key
                        if key in entry or any(key in s for s in entry.get("senses", [])):
                            found_count += 1
                            if found_count <= 2:
                                print(f"Found occurrence in word: {entry.get('word')}")
                    except:
                        pass

    except Exception as e:
        print(f"Error reading {path}: {e}")

    print(f"Total occurrences found in first {limit_mb}MB: {found_count}")


if __name__ == "__main__":
    scan_for_key("data/01_raw/fr-wiktionary-kaikki.jsonl", "translations")
    scan_for_key("data/01_raw/de-wiktionary-kaikki.jsonl", "translations")
