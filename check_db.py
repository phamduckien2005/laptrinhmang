import sqlite3, os

db_path = r'c:\Users\phamk\OneDrive\Desktop\testunilib\backend\instance\data.db'
print('DB exists:', os.path.exists(db_path))

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# List tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
print('\n=== TABLES ===')
for t in tables:
    print(' -', t[0])

# Count books
try:
    cur.execute('SELECT COUNT(*) FROM book')
    count = cur.fetchone()[0]
    print(f'\n=== BOOK COUNT: {count} ===')
    
    cur.execute('SELECT id, title, author, available FROM book LIMIT 10')
    rows = cur.fetchall()
    print('=== FIRST 10 BOOKS ===')
    for r in rows:
        print(r)
except Exception as e:
    print('Book query error:', e)

# Count users
try:
    cur.execute('SELECT COUNT(*) FROM user')
    print(f'\n=== USER COUNT: {cur.fetchone()[0]} ===')
except Exception as e:
    print('User query error:', e)

conn.close()
