"""
Test the database management functionality
"""

import unittest
import sys
import os
import sqlite3
import tempfile
# from datetime import datetime # Not currently used in this test file

# Adjust the path to import from the src directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
# Ensure correct import based on the refactored manager.py location
from src.database.manager import DatabaseManager

class TestDatabaseManager(unittest.TestCase):
    """Test cases for the database manager"""

    def setUp(self):
        """Set up test environment before each test"""
        # Create a temporary directory and file for the test database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_database.db")

        # Instantiate the DatabaseManager using the temporary path
        self.db = DatabaseManager(db_path=self.db_path) # Pass the temp path

    def tearDown(self):
        """Clean up after test"""
        # Remove the temporary database file and directory
        if hasattr(self, 'db_path') and os.path.exists(self.db_path):
            # Optional: Close any lingering connections if needed, though manager should handle it
            # if hasattr(self, 'conn') and self.conn:
            #     self.conn.close()
            os.remove(self.db_path)
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
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

        # Verify it was added using the manager's method
        # Note: get_monitored_accounts returns [(username, platform, last_checked)]
        accounts = self.db.get_monitored_accounts(active_only=False) # Check all accounts
        self.assertEqual(len(accounts), 1, "Should have one monitored account")
        self.assertEqual(accounts[0][0], "test_account", "Account username should match")
        self.assertEqual(accounts[0][1], "instagram", "Account platform should match")


    def test_add_processed_post(self):
        """Test adding a processed post"""
        # Prerequisite: Add a monitored account first (for potential FOREIGN KEY)
        self.db.add_monitored_account("test_account", "instagram")

        # --- CORRECTED INDENTATION START ---
        # Add a test processed post
        success = self.db.add_processed_post(
            post_id="12345",
            post_url="https://www.instagram.com/p/test123/",
            monitored_account="test_account", # Correct keyword argument
            platform="instagram"              # Added platform argument
        )
        # self.assertTrue(success, "Adding processed post should return success indication") # Optional check of return value

        # Verify it was added directly via SQLite connection
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT post_id, monitored_account, platform FROM processed_posts WHERE post_id = ?", ("12345",))
        result = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(result, "Post should be stored in database")
        self.assertEqual(result[0], "12345", "Post ID should match")
        self.assertEqual(result[1], "test_account", "Monitored account should match")
        self.assertEqual(result[2], "instagram", "Platform should match")
        # --- CORRECTED INDENTATION END ---


    def test_add_detected_bot(self):
        """Test adding a detected bot"""
        # Set up prerequisites (account and processed post)
        self.db.add_monitored_account("test_account", "instagram")
        # Need to use the corrected call here too
        self.db.add_processed_post(
            post_id="12345",
            post_url="https://www.instagram.com/p/test123/",
            monitored_account="test_account",
            platform="instagram"
        )

        # Add a detected bot
        bot_id = self.db.add_detected_bot(
            username="suspected_bot",
            comment_id="c123",
            post_id="12345",
            bot_likelihood=0.85,
            comment_text="Check out my profile!",
            indicators={'spammy': 1, 'link_in_bio': 1} # Example indicators
        )
        self.assertIsNotNone(bot_id, "add_detected_bot should return the new bot ID")

        # Verify it was added directly via SQLite
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Select relevant fields, including indicators
        cursor.execute("""SELECT username, bot_likelihood, comment_id, post_id, indicators
                          FROM detected_bots WHERE id = ?""", (bot_id,))
        result = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(result, "Bot detection should be stored in database")
        self.assertEqual(result[0], "suspected_bot", "Bot username should match")
        self.assertEqual(result[1], 0.85, "Bot likelihood should match")
        self.assertEqual(result[2], "c123", "Comment ID should match")
        self.assertEqual(result[3], "12345", "Post ID should match")
        self.assertEqual(result[4], "link_in_bio,spammy", "Indicators string should match (sorted keys)") # Check stored string

# Standard unittest runner
if __name__ == '__main__':
    unittest.main()