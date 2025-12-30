import psycopg2
import sys

# Set UTF-8 encoding for console output on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Use credentials from conf/local/credentials.yml
conn = psycopg2.connect('postgresql://postgres:rosetta_password@localhost:5432/rosetta')
cur = conn.cursor()

# Check for any "Ayala" titles in the results
print('Searching for "Ayala" in Hebrew titles:')
print('-' * 100)
cur.execute("""
    SELECT he_title, match_title, score, author_filtered, is_translation
    FROM aligned_catalogs
    WHERE he_title LIKE '%איאלה%' OR he_title LIKE '%אילה%' OR he_title LIKE '%איילה%'
""")
rows = cur.fetchall()
if rows:
    for row in rows:
        print(f'{row[0][:35]:35} -> {row[1][:35]:35} | Score: {row[2]:.3f} | Author: {row[3]} | Trans: {row[4]}')
else:
    print('No Ayala titles found in alignment results!')

print('\n\nSearching for "Ayala" in English/Spanish matched titles:')
print('-' * 100)
cur.execute("""
    SELECT he_title, match_title, score, author_filtered, is_translation
    FROM aligned_catalogs
    WHERE match_title LIKE '%Ayala%'
""")
rows = cur.fetchall()
if rows:
    for row in rows:
        print(f'{row[0][:35]:35} -> {row[1][:35]:35} | Score: {row[2]:.3f} | Author: {row[3]} | Trans: {row[4]}')
else:
    print('No Ayala titles found in matched English/Spanish titles!')

conn.close()
