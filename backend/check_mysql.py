import os

import pymysql
from dotenv import load_dotenv


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

connection = pymysql.connect(
    host=os.getenv("MYSQL_HOST", "127.0.0.1"),
    port=int(os.getenv("MYSQL_PORT", "3306")),
    user=os.getenv("MYSQL_USER", "root"),
    password=os.getenv("MYSQL_PASSWORD", ""),
    database=os.getenv("MYSQL_DATABASE", "unilib"),
    charset="utf8mb4",
    cursorclass=pymysql.cursors.Cursor,
)

with connection:
    with connection.cursor() as cur:
        cur.execute("SHOW TABLES")
        tables = [row[0] for row in cur.fetchall()]

        print("=== TABLES ===")
        for table in tables:
            print(" -", table)

        print("\n=== COLUMNS ===")
        for table in tables:
            print(f"\n[{table}]")
            cur.execute(f"SHOW COLUMNS FROM `{table}`")
            for field, data_type, nullable, key, default, extra in cur.fetchall():
                print(f" - {field}: {data_type}, null={nullable}, key={key}, default={default}, extra={extra}")

        for table in ("book", "user", "borrow_record"):
            if table in tables:
                cur.execute(f"SELECT COUNT(*) FROM `{table}`")
                print(f"\n{table} count:", cur.fetchone()[0])
