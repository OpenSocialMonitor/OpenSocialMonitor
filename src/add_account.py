import sys
import argparse
import os
from dotenv import load_dotenv

# Load environment variables from .env file FIRST
# This makes INSTAGRAM_USERNAME/PASSWORD available via os.environ
load_dotenv()

# Now import other modules that might use environment variables indirectly
# Import the db instance from the database package's __init__.py
from src.database import db
# Import the platform class - it should handle its own auth using os.environ
from src.platforms.instagram import InstagramPlatform

def add_account(username, platform='instagram'):
    """Add an account to the monitoring list, with optional verification."""
    print(f"Attempting to add @{username} for {platform} monitoring...")

    # Optional: Verify account existence using the platform connector
    should_add = True # Default to adding even if verification fails/skipped
    try:
        print("  Verifying account existence via Instagram API (requires login)...")
        # InstagramPlatform constructor should handle authentication using loaded env vars
        platform_conn = InstagramPlatform()
        if hasattr(platform_conn, 'client') and platform_conn.client is not None: # Check if client exists and is not None
            user_info = platform_conn.get_user_info(username)
        else:
            print("  ⚠️ Warning: Could not verify account (Instagram login failed/credentials missing or client object not initialized).")
            proceed = input("  Verification failed. Add to monitoring list anyway? (y/n): ")
            if proceed.lower() != 'y':
                should_add = False
                print("  Aborted adding account.")

    except Exception as e:
        print(f"  ⚠️ Warning: Error during account verification: {e}")
        # Ask user if they want to add anyway
        proceed = input("  Verification failed due to error. Add to monitoring list anyway? (y/n): ")
        if proceed.lower() != 'y':
            should_add = False
            print("  Aborted adding account.")

    # Proceed to add to database if verification passed or user confirmed
    if should_add:
        print(f"  Adding @{username} to the database...")
        # Use the 'add_monitored_account' method from our 'db' instance
        success = db.add_monitored_account(username, platform)

        if success:
            print(f"✅ Account @{username} added successfully to the monitoring list.")
        else:
            # Check if it failed because it already exists or due to DB error
            print(f"ℹ️ Account @{username} might already be in the monitoring list, or a DB error occurred.")
        return success
    else:
        return False # Did not add the account

def list_accounts():
    """List all monitored accounts from the database."""
    # Use the 'get_all_monitored_accounts_details' method from our 'db' instance
    accounts = db.get_all_monitored_accounts_details()

    if not accounts:
        print("No accounts are currently configured for monitoring.")
    else:
        print("\n--- Monitored Accounts ---")
        print("-" * 75) # Adjusted width
        print(f"{'Username':<25} {'Platform':<12} {'Last Checked':<25} {'Active'}")
        print("-" * 75)
        for username, platform, last_checked, active in accounts:
            status = "Yes" if active else "No"
            last_checked_str = last_checked if last_checked else "Never"
            # Ensure last_checked_str fits; truncate if necessary
            print(f"{username:<25} {platform:<12} {last_checked_str:<25.25} {status}")
        print("-" * 75)

def enable_account(username):
    """Enable monitoring for a specific account."""
    print(f"Attempting to enable monitoring for @{username}...")
    # Use the 'update_account_status' method from our 'db' instance
    success = db.update_account_status(username, active=True)
    if success:
        print(f"✅ Monitoring enabled for @{username}.")
    else:
        print(f"❌ Account @{username} not found in the database or DB error occurred.")

def disable_account(username):
    """Disable monitoring for a specific account."""
    print(f"Attempting to disable monitoring for @{username}...")
    # Use the 'update_account_status' method from our 'db' instance
    success = db.update_account_status(username, active=False)
    if success:
        print(f"✅ Monitoring disabled for @{username}.")
    else:
        print(f"❌ Account @{username} not found in the database or DB error occurred.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Manage monitored social media accounts.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', help='Command to execute', required=True)

    # Add command
    add_parser = subparsers.add_parser('add', help='Add an account to monitor (verifies if possible)')
    add_parser.add_argument('username', help='Username of the account to add')
    add_parser.add_argument('--platform', default='instagram', choices=['instagram'], help='Platform (currently only Instagram)')

    # List command
    list_parser = subparsers.add_parser('list', help='List all configured monitored accounts')

    # Enable command
    enable_parser = subparsers.add_parser('enable', help='Enable monitoring for an existing account')
    enable_parser.add_argument('username', help='Username to enable')

    # Disable command
    disable_parser = subparsers.add_parser('disable', help='Disable monitoring for an existing account')
    disable_parser.add_argument('username', help='Username to disable')

    args = parser.parse_args()

    # Ensure database schema exists before running commands
    # The DatabaseManager __init__ handles this when 'db' is imported
    # try:
    #     db.initialize_database() # Not needed if __init__ calls it
    # except Exception as e:
    #     print(f"FATAL: Could not initialize database: {e}")
    #     sys.exit(1)

    # Execute the chosen command
    if args.command == 'add':
        add_account(args.username, args.platform)
    elif args.command == 'list':
        list_accounts()
    elif args.command == 'enable':
        enable_account(args.username)
    elif args.command == 'disable':
        disable_account(args.username)
    else:
        parser.print_help()