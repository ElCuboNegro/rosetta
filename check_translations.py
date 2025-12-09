import gzip
import json
import sys

# Set UTF-8 encoding for output
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

count = 0
he_count = 0

with gzip.open('data/01_raw/es-wiktionary-kaikki.jsonl.gz', 'rt', encoding='utf-8') as f:
    for line in f:
        entry = json.loads(line)
        if entry.get('lang_code') == 'es':
            count += 1
            trans = entry.get('translations', [])
            has_he = any(t.get('lang_code') == 'he' for t in trans)
            if has_he:
                he_count += 1
                if he_count <= 5:
                    he_words = [t['word'] for t in trans if t.get('lang_code') == 'he']
                    print(f"Word: {entry['word']} - Hebrew translations: {he_words}")
        if count >= 50000:
            break

print(f'\nOut of first {count} Spanish entries, {he_count} have Hebrew translations ({100*he_count/count:.2f}%)')
