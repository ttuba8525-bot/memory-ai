import sqlite3
import os

db_path = os.path.join("instance", "dejavu.db")

if not os.path.exists(db_path):
    print("Database not found, no migration needed.")
else:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT 1")
    except sqlite3.OperationalError:
        print("Column is_verified already exists or error.")
    
    try:
        c.execute("ALTER TABLE users ADD COLUMN verification_token VARCHAR(100)")
    except sqlite3.OperationalError:
        print("Column verification_token already exists or error.")
        
    conn.commit()
    conn.close()
    print("Database migration complete.")
