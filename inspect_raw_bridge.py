import json


def inspect_dump(path, lang_name):
    print(f"--- Inspecting {lang_name} ({path}) ---")
    try:
        target_lang = "fr" if lang_name == "French" else "de"
        print(f"Searching for first {target_lang} entry...")

        found_entry = None
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                entry = json.loads(line)
                if entry.get("lang_code") == target_lang:
                    # Look for one with non-empty senses to be useful
                    if entry.get("senses"):
                        found_entry = entry
                        break

        if found_entry:
            filename = f"sample_{target_lang}_entry.json"
            with open(filename, "w", encoding="utf-8") as out:
                json.dump(found_entry, out, indent=2, ensure_ascii=False)
            print(f"Saved sample entry to {filename}")
        else:
            print(f"No suitable {target_lang} entry found.")

    except Exception as e:
        print(f"Error reading {path}: {e}")


if __name__ == "__main__":
    inspect_dump("data/01_raw/fr-wiktionary-kaikki.jsonl", "French")
    inspect_dump("data/01_raw/de-wiktionary-kaikki.jsonl", "German")
