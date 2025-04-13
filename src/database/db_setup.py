import sqlite3
import os

def setup_database():
    # Make sure we're in the project directory
    db_path = 'instagram_bot_monitor.db'
    
    # Create or connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS monitored_accounts (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE,
        last_checked TIMESTAMP,
        active BOOLEAN DEFAULT 1
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS processed_posts (
        id INTEGER PRIMARY KEY,
        post_id TEXT UNIQUE,
        post_url TEXT,
        username TEXT,
        processed_date TIMESTAMP,
        FOREIGN KEY (username) REFERENCES monitored_accounts(username)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS detected_bots (
        id INTEGER PRIMARY KEY,
        username TEXT,
        comment_id TEXT,
        post_id TEXT,
        bot_likelihood REAL,
        comment_text TEXT,
        detection_date TIMESTAMP,
        warning_sent BOOLEAN DEFAULT 0,
        warning_approved BOOLEAN DEFAULT 0,
        FOREIGN KEY (post_id) REFERENCES processed_posts(post_id)
    )
    ''')
    
    conn.commit()
    conn.close()
    print("Database setup complete.")
    print(f"Database created at: {os.path.abspath(db_path)}")

if __name__ == "__main__":
    setup_database()