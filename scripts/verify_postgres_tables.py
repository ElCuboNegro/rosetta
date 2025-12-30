import psycopg2
import sys

# Set UTF-8 encoding for console output on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Use credentials from conf/local/credentials.yml
conn = psycopg2.connect('postgresql://postgres:rosetta_password@localhost:5432/rosetta')
cur = conn.cursor()

# Get all tables
cur.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    ORDER BY table_name
""")

tables = cur.fetchall()
print(f"Total tables in PostgreSQL: {len(tables)}\n")
print("Tables:")
print("-" * 80)

table_info = []
for table in tables:
    table_name = table[0]
    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cur.fetchone()[0]
    table_info.append((table_name, count))
    print(f"{table_name:40} | {count:>10} rows")

print("\n" + "=" * 80)
print(f"Total: {len(tables)} tables")

conn.close()
