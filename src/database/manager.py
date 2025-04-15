"""
Database management for social media bot detection
"""

import sqlite3
import os
import datetime
import random
from dotenv import load_dotenv

class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self, db_path='instagram_bot_monitor.db'):
        """Initialize database manager"""
        self.db_path = db_path
        self.ensure_tables_exist()
    
    def get_connection(self):
        """Get a database connection"""
        return sqlite3.connect(self.db_path)
    
    def ensure_tables_exist(self):
        """Ensure all required tables exist in database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create tables (using your existing schema from db_setup.py)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS monitored_accounts (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            platform TEXT DEFAULT 'instagram',
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
        
    def add_monitored_account(self, username, platform='instagram'):
        """Add an account to the monitoring list"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        now = datetime.datetime.now()
        
        try:
            cursor.execute("""
            INSERT INTO monitored_accounts (username, platform, last_checked)
            VALUES (?, ?, ?)
            """, (username, platform, now))
            
            conn.commit()
            success = True
            print(f"Account @{username} added to monitoring list")
        except sqlite3.IntegrityError:
            success = False
            print(f"Account @{username} is already in the monitoring list")
        
        conn.close()
        return success
    
    def get_monitored_accounts(self, active_only=True):
        """List all monitored accounts"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if active_only:
            cursor.execute("SELECT username, platform, last_checked FROM monitored_accounts WHERE active = 1")
        else:
            cursor.execute("SELECT username, platform, last_checked, active FROM monitored_accounts")
        
        accounts = cursor.fetchall()
        conn.close()
        
        return accounts
    
    def add_processed_post(self, post_id, post_url, username, platform='instagram'):
        """Add a processed post to the database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        now = datetime.datetime.now()
        
        cursor.execute("""
        INSERT OR IGNORE INTO processed_posts (post_id, post_url, username, processed_date)
        VALUES (?, ?, ?, ?)
        """, (post_id, post_url, username, now))
        
        conn.commit()
        conn.close()
    
    def add_detected_bot(self, username, comment_id, post_id, bot_likelihood, comment_text):
        """Add a detected bot to the database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        now = datetime.datetime.now()
        
        cursor.execute("""
        INSERT INTO detected_bots 
        (username, comment_id, post_id, bot_likelihood, comment_text, detection_date)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (username, comment_id, post_id, bot_likelihood, comment_text, now))
        
        bot_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return bot_id
    
    def get_pending_bots(self):
        """Get all detected bots pending approval"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT db.id, db.username, db.bot_likelihood, db.comment_text, pp.post_url, db.detection_date
        FROM detected_bots db
        JOIN processed_posts pp ON db.post_id = pp.post_id
        WHERE db.warning_sent = 0
        ORDER BY db.detection_date DESC
        """)
        
        bots = cursor.fetchall()
        conn.close()
        
        return bots
    
    def get_bot_details(self, bot_id):
        """Get detailed information about a detected bot"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT db.username, db.bot_likelihood, db.comment_text, pp.post_url, db.detection_date,
               db.warning_sent, db.comment_id, db.post_id
        FROM detected_bots db
        JOIN processed_posts pp ON db.post_id = pp.post_id
        WHERE db.id = ?
        """, (bot_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result
    
    def update_bot_warning_status(self, bot_id, warning_sent=True, warning_approved=True):
        """Update warning status for a bot"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        UPDATE detected_bots 
        SET warning_sent = ?, warning_approved = ? 
        WHERE id = ?
        """, (1 if warning_sent else 0, 1 if warning_approved else 0, bot_id))
        
        conn.commit()
        affected_rows = cursor.rowcount
        conn.close()
        
        return affected_rows > 0