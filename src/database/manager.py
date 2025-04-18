import sqlite3
import os
import datetime

# Define DB file path at the module level or within the class __init__
DB_FILE = 'instagram_bot_monitor.db'

class DatabaseManager:
    """Manages database connections and operations for OpenSocialMonitor."""

    def __init__(self, db_path=DB_FILE):
        """
        Initialize database manager. Ensures the database file exists
        and the necessary tables are created.
        """
        self.db_path = db_path
        self._initialize_database() # Changed to call internal init method

    def get_connection(self):
        """Establishes and returns a connection to the SQLite database."""
        try:
            conn = sqlite3.connect(self.db_path)
            # Optional: Improve debugging by returning rows as dictionaries
            # conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            print(f"Database connection error to {self.db_path}: {e}")
            # Depending on severity, you might want to raise the error
            # raise e
            return None # Indicate failure

    def _initialize_database(self):
        """
        Internal method to initialize the database schema if it doesn't exist.
        Called automatically when DatabaseManager is instantiated.
        """
        conn = self.get_connection()
        if conn is None:
            print("FATAL: Cannot initialize database - connection failed.")
            return # Cannot proceed without connection

        cursor = conn.cursor()
        try:
            # --- Create monitored_accounts table ---
            # Use TEXT for username PRIMARY KEY for flexibility
            # Store platform name
            # Use ISO format TEXT for timestamps for better compatibility
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS monitored_accounts (
                username TEXT PRIMARY KEY NOT NULL,
                platform TEXT NOT NULL DEFAULT 'instagram',
                last_checked TEXT,
                added_date TEXT DEFAULT CURRENT_TIMESTAMP,
                active INTEGER DEFAULT 1 CHECK(active IN (0, 1))
            )
            """)

            # --- Create processed_posts table ---
            # Ensure FOREIGN KEY references the correct primary key (username)
            # Add ON DELETE CASCADE/SET NULL depending on desired behavior
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_posts (
                post_id TEXT PRIMARY KEY NOT NULL,
                post_url TEXT NOT NULL,
                monitored_account TEXT,
                platform TEXT,
                processed_date TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (monitored_account) REFERENCES monitored_accounts(username) ON DELETE SET NULL
            )
            """)
            # Added index for faster post_id lookups if needed (optional)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_processed_posts_post_id ON processed_posts(post_id)")


            # --- Create detected_bots table ---
            # Ensure FOREIGN KEY references the correct primary key (post_id)
            # Allow bot_likelihood to be NULL if calculation fails
            # Use INTEGER for boolean flags
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS detected_bots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                comment_id TEXT UNIQUE, -- Assuming comment ID should be unique? Or unique per post?
                post_id TEXT NOT NULL,
                bot_likelihood REAL,
                comment_text TEXT,
                indicators TEXT, -- Store as JSON string or comma-separated
                detection_date TEXT DEFAULT CURRENT_TIMESTAMP,
                warning_sent INTEGER DEFAULT 0 CHECK(warning_sent IN (0, 1)),
                warning_approved INTEGER DEFAULT 0 CHECK(warning_approved IN (0, 1)), -- 0=pending/rejected, 1=approved
                FOREIGN KEY (post_id) REFERENCES processed_posts(post_id) ON DELETE CASCADE
            )
            """)
            # Added index for faster lookups by post_id (optional)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_detected_bots_post_id ON detected_bots(post_id)")

            conn.commit()
            # print("Database schema checked/initialized.") # Keep quiet unless debugging
        except sqlite3.Error as e:
            print(f"Database schema initialization error: {e}")
            conn.rollback() # Roll back changes if error occurs during setup
        finally:
            if conn:
                conn.close()

    # === Account Management Methods ===

    def add_monitored_account(self, username, platform='instagram'):
        """Adds an account to the monitoring list."""
        conn = self.get_connection()
        if conn is None: return False
        cursor = conn.cursor()
        success = False
        try:
            # Use default for added_date, only set username/platform
            cursor.execute("""
            INSERT INTO monitored_accounts (username, platform)
            VALUES (?, ?)
            """, (username, platform))
            conn.commit()
            success = True
        except sqlite3.IntegrityError:
            # Username already exists (PRIMARY KEY constraint)
            print(f"Info: Account @{username} already exists in monitoring list.")
            success = False # Indicate not added
        except sqlite3.Error as e:
            print(f"Error adding account {username} to DB: {e}")
            conn.rollback()
            success = False
        finally:
            if conn:
                conn.close()
        return success

    def get_monitored_accounts(self, active_only=True):
        """Retrieves monitored accounts based on active status."""
        conn = self.get_connection()
        if conn is None: return []
        cursor = conn.cursor()
        accounts = []
        try:
            query = "SELECT username, platform, last_checked FROM monitored_accounts"
            if active_only:
                query += " WHERE active = 1"
            query += " ORDER BY username"
            cursor.execute(query)
            accounts = cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error retrieving monitored accounts: {e}")
        finally:
            if conn:
                conn.close()
        # Returns list of tuples: [(username, platform, last_checked), ...]
        return accounts

    def get_all_monitored_accounts_details(self):
        """Retrieves full details for all monitored accounts (for listing)."""
        conn = self.get_connection()
        if conn is None: return []
        cursor = conn.cursor()
        accounts = []
        try:
            query = "SELECT username, platform, last_checked, active FROM monitored_accounts ORDER BY username"
            cursor.execute(query)
            accounts = cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error retrieving all account details: {e}")
        finally:
            if conn:
                conn.close()
        # Returns list of tuples: [(username, platform, last_checked, active), ...]
        return accounts

    def update_account_status(self, username, active):
        """Enables (active=True) or disables (active=False) monitoring for an account."""
        conn = self.get_connection()
        if conn is None: return False
        cursor = conn.cursor()
        success = False
        try:
            cursor.execute("""
            UPDATE monitored_accounts
            SET active = ?
            WHERE username = ?
            """, (1 if active else 0, username))
            updated_rows = cursor.rowcount
            conn.commit()
            success = updated_rows > 0 # True if a row was actually updated
        except sqlite3.Error as e:
            print(f"Error updating status for account @{username}: {e}")
            conn.rollback()
            success = False
        finally:
            if conn:
                conn.close()
        return success

    def update_last_checked(self, username):
        """Updates the 'last_checked' timestamp for a monitored account."""
        conn = self.get_connection()
        if conn is None: return False
        cursor = conn.cursor()
        success = False
        try:
            # Use standard ISO 8601 format for timestamp
            timestamp = datetime.datetime.now().isoformat()
            cursor.execute("""
            UPDATE monitored_accounts
            SET last_checked = ?
            WHERE username = ?
            """, (timestamp, username))
            conn.commit()
            success = cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error updating last_checked for @{username}: {e}")
            conn.rollback()
            success = False
        finally:
            if conn:
                conn.close()
        return success

    # === Post Processing Methods ===

    def add_processed_post(self, post_id, post_url, monitored_account, platform):
        """Adds a record for a processed post, ignoring if it already exists."""
        conn = self.get_connection()
        if conn is None: return False
        cursor = conn.cursor()
        success = False
        try:
            # Use default for processed_date
            cursor.execute("""
            INSERT OR IGNORE INTO processed_posts (post_id, post_url, monitored_account, platform)
            VALUES (?, ?, ?, ?)
            """, (post_id, post_url, monitored_account, platform))
            conn.commit()
            # Check if insert happened or was ignored
            success = cursor.lastrowid is not None or cursor.rowcount > 0 # May vary slightly by SQLite version
        except sqlite3.Error as e:
            print(f"Error adding processed post {post_id}: {e}")
            conn.rollback()
            success = False
        finally:
            if conn:
                conn.close()
        return success

    def check_if_post_processed(self, post_id):
        """Checks if a specific post_id exists in the processed_posts table."""
        conn = self.get_connection()
        if conn is None: return False # Assume not processed if DB fails
        cursor = conn.cursor()
        processed = False
        try:
            cursor.execute("SELECT 1 FROM processed_posts WHERE post_id = ? LIMIT 1", (post_id,))
            result = cursor.fetchone()
            processed = result is not None
        except sqlite3.Error as e:
            print(f"Error checking if post {post_id} was processed: {e}")
            processed = False # Treat error as not processed
        finally:
            if conn:
                conn.close()
        return processed

    # === Bot Detection Methods ===

    def add_detected_bot(self, username, comment_id, post_id, bot_likelihood, comment_text, indicators=None):
        """Adds a record for a newly detected bot."""
        conn = self.get_connection()
        if conn is None: return None # Return None for bot_id on failure
        cursor = conn.cursor()
        bot_id = None
        # Convert indicators dict to string (e.g., comma-separated keys)
        indicators_str = ','.join(sorted(indicators.keys())) if indicators else None
        try:
            # Use defaults for detection_date, warning_sent, warning_approved
            cursor.execute("""
            INSERT INTO detected_bots (username, comment_id, post_id, bot_likelihood, comment_text, indicators)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (username, comment_id, post_id, bot_likelihood, comment_text, indicators_str))
            bot_id = cursor.lastrowid # Get the ID of the inserted row
            conn.commit()
        except sqlite3.IntegrityError as e:
             # Handle potential unique constraint violation if comment_id is made unique
             print(f"Info: Bot detection for comment ID {comment_id} might already exist: {e}")
             conn.rollback()
             bot_id = None # Indicate failure or duplicate
        except sqlite3.Error as e:
            print(f"Error adding detected bot @{username} for post {post_id}: {e}")
            conn.rollback()
            bot_id = None
        finally:
            if conn:
                conn.close()
        return bot_id # Return the new bot's ID or None

    def get_pending_bots(self):
        """Retrieves bot detections pending review (approved=0, sent=0)."""
        conn = self.get_connection()
        if conn is None: return []
        cursor = conn.cursor()
        bots = []
        try:
            # Select necessary fields for listing
            cursor.execute("""
            SELECT db.id, db.username, db.bot_likelihood, db.comment_text, pp.post_url, db.detection_date
            FROM detected_bots db
            JOIN processed_posts pp ON db.post_id = pp.post_id
            WHERE db.warning_approved = 0 AND db.warning_sent = 0
            ORDER BY db.detection_date DESC
            """)
            bots = cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error retrieving pending bots: {e}")
        finally:
            if conn:
                conn.close()
        # Returns list of tuples: [(id, username, likelihood, comment, post_url, detected_date), ...]
        return bots

    def get_bot_details(self, bot_id):
        """Retrieves full details for a specific bot detection ID."""
        conn = self.get_connection()
        if conn is None: return None
        cursor = conn.cursor()
        result = None
        try:
            # Select all relevant fields for viewing/action
            cursor.execute("""
            SELECT db.username, db.bot_likelihood, db.comment_text, pp.post_url,
                   db.detection_date, db.warning_sent, db.warning_approved,
                   db.comment_id, db.post_id, db.indicators
            FROM detected_bots db
            JOIN processed_posts pp ON db.post_id = pp.post_id
            WHERE db.id = ?
            """, (bot_id,))
            result = cursor.fetchone()
        except sqlite3.Error as e:
            print(f"Error retrieving details for bot ID {bot_id}: {e}")
        finally:
            if conn:
                conn.close()
        # Returns tuple: (username, likelihood, ..., comment_id, post_id, indicators) or None
        return result

    def update_bot_warning_status(self, bot_id, sent, approved):
        """Updates the warning_sent and warning_approved status for a bot detection."""
        conn = self.get_connection()
        if conn is None: return False
        cursor = conn.cursor()
        success = False
        try:
            cursor.execute("""
            UPDATE detected_bots
            SET warning_sent = ?, warning_approved = ?
            WHERE id = ?
            """, (1 if sent else 0, 1 if approved else 0, bot_id))
            updated_rows = cursor.rowcount
            conn.commit()
            success = updated_rows > 0
        except sqlite3.Error as e:
            print(f"Error updating warning status for bot ID {bot_id}: {e}")
            conn.rollback()
            success = False
        finally:
            if conn:
                conn.close()
        return success

# Optional: Add a main block for direct testing if needed
# if __name__ == '__main__':
#     print("Testing DatabaseManager setup...")
#     db_manager = DatabaseManager() # This will initialize the DB
#     print(f"Database file: {os.path.abspath(db_manager.db_path)}")
#     print("Getting connection...")
#     conn = db_manager.get_connection()
#     if conn:
#         print("Connection successful.")
#         conn.close()
#     else:
#         print("Connection failed.")
#     print("Test complete.")
# --- END COPY ---