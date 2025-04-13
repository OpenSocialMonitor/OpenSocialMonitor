"""
Test the database management functionality
"""

import unittest
import sys
import os
import sqlite3
import tempfile
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from src.database.manager import DatabaseManager

class TestDatabaseManager(unittest.TestCase):
    """Test cases for the database manager"""
    
    def setUp(self):
        """Set up test environment before each test"""
        # Create a temporary file for the test database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_database.db")
        
        # Create the database manager
        self.db = DatabaseManager(self.db_path)
    
    def tearDown(self):
        """Clean up after test"""
        # Remove the temporary database file
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_initialization(self):
        """Test that the database initializes correctly"""
        # Verify tables exist by checking directly with SQLite
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if the tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='monitored_accounts'")
        self.assertIsNotNone(cursor.fetchone(), "monitored_accounts table should exist")
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='processed_posts'")
        self.assertIsNotNone(cursor.fetchone(), "processed_posts table should exist")
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='detected_bots'")
        self.assertIsNotNone(cursor.fetchone(), "detected_bots table should exist")
        
        conn.close()
    
    def test_add_monitored_account(self):
        """Test adding a monitored account"""
        # Add a test account
        success = self.db.add_monitored_account("test_account", "instagram")
        self.assertTrue(success, "Should successfully add account")
        
        # Verify it was added
        accounts = self.db.get_monitored_accounts()
        self.assertEqual(len(accounts), 1, "Should have one monitored account")
        self.assertEqual(accounts[0][0], "test_account", "Account username should match")
    
    def test_add_processed_post(self):
        """Test adding a processed post"""
        # Add a test account first (for foreign key constraint)
        self.db.add_monitored_account("test_account", "instagram")
        
        # Add a test post
        self.db.add_processed_post(
            post_id="12345",
            post_url="https://www.instagram.com/p/test123/",
            username="test_account"
        )
        
        # Verify it was added
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT post_id FROM processed_posts WHERE post_id = ?", ("12345",))
        result = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(result, "Post should be stored in database")
        self.assertEqual(result[0], "12345", "Post ID should match")
    
    def test_add_detected_bot(self):
        """Test adding a detected bot"""
        # Set up prerequisites
        self.db.add_monitored_account("test_account", "instagram")
        self.db.add_processed_post("12345", "https://www.instagram.com/p/test123/", "test_account")
        
        # Add a detected bot
        bot_id = self.db.add_detected_bot(
            username="suspected_bot",
            comment_id="c123",
            post_id="12345",
            bot_likelihood=0.85,
            comment_text="Check out my profile for amazing deals!"
        )
        
        # Verify it was added
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT username, bot_likelihood FROM detected_bots WHERE id = ?", (bot_id,))
        result = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(result, "Bot detection should be stored in database")
        self.assertEqual(result[0], "suspected_bot", "Bot username should match")
        self.assertEqual(result[1], 0.85, "Bot likelihood should match")

if __name__ == '__main__':
    unittest.main()