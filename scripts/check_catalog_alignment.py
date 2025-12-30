import psycopg2
import os
import sys

# Set UTF-8 encoding for console output on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Use credentials from conf/local/credentials.yml
conn = psycopg2.connect('postgresql://postgres:rosetta_password@localhost:5432/rosetta')
cur = conn.cursor()

# Get total count
cur.execute('SELECT COUNT(*) FROM aligned_catalogs')
total = cur.fetchone()[0]
print(f'Total catalog alignments: {total}\n')

# Check for problematic cases (high score but no author filter for translations)
cur.execute("""
    SELECT he_title, match_title, score, author_filtered, is_translation
    FROM aligned_catalogs
    WHERE is_translation = true AND author_filtered = false
    ORDER BY score DESC
    LIMIT 20
""")
print('Translations without author filtering (potential false positives):')
print('-' * 100)
rows = cur.fetchall()
for row in rows:
    print(f'{row[0][:35]:35} -> {row[1][:35]:35} | Score: {row[2]:.3f}')

# Check for specific problematic cases mentioned in the issue
print('\n\nSearching for Ayala/Ilíada case:')
print('-' * 100)
cur.execute("""
    SELECT he_title, match_title, score, author_filtered, is_translation
    FROM aligned_catalogs
    WHERE he_title LIKE '%Ayala%' OR match_title LIKE '%Ilíada%' OR match_title LIKE '%Iliada%'
""")
rows = cur.fetchall()
for row in rows:
    print(f'{row[0][:35]:35} -> {row[1][:35]:35} | Score: {row[2]:.3f} | Author: {row[3]} | Trans: {row[4]}')

conn.close()
