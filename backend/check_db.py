import sqlite3
import os

def check_db(db_name):
    db_path = os.path.join(os.getcwd(), db_name)
    print(f"--- Checking {db_path} ---")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("Tables:", tables)
        for table in tables:
            table_name = table[0]
            if table_name in ('posts', 'forum_posts', 'post'):
                print(f"\nTable {table_name}:")
                cursor.execute(f"SELECT * FROM {table_name}")
                rows = cursor.fetchall()
                for row in rows:
                    print(row)
    except Exception as e:
        print(f"Error: {e}")

check_db('sqlite.db')
check_db('test_forum.db')
