"""
Account management for OpenSocialMonitor

This script allows you to add, list, enable, or disable accounts for monitoring.
"""

import sys
import argparse
from src.database import db
from src.platforms.instagram import InstagramPlatform

def add_account(username, platform='instagram'):
    """Add an account to the monitoring list"""
    print(f"Adding @{username} to monitoring list...")
    
    # Verify that the account exists before adding
    platform_conn = InstagramPlatform()
    if platform_conn.login():
        user_info = platform_conn.get_user_info(username)
        if not user_info:
            print(f"❌ Could not find account @{username} on {platform}")
            return False
        
        print(f"✅ Account verified: @{username} ({user_info.get('follower_count', 0)} followers)")
    else:
        print("⚠️ Could not verify account (login failed)")
        print("Adding anyway, but please verify the username is correct")
    
    # Add to database
    success = db.add_monitored_account(username, platform)
    
    if success:
        print(f"✅ Account @{username} added to monitoring list")
    else:
        print(f"ℹ️ Account @{username} is already in the monitoring list")
    
    return success

def list_accounts():
    """List all monitored accounts"""
    accounts = db.get_monitored_accounts(active_only=False)
    
    if not accounts:
        print("No accounts are currently being monitored")
    else:
        print("\nMonitored Accounts:")
        print("-" * 70)
        print(f"{'Username':<20} {'Platform':<12} {'Last Checked':<30} {'Active'}")
        print("-" * 70)
        
        for username, platform, last_checked, active in accounts:
            status = "Yes" if active else "No"
            print(f"{username:<20} {platform:<12} {last_checked:<30} {status}")

def enable_account(username):
    """Enable monitoring for an account"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    UPDATE monitored_accounts
    SET active = 1
    WHERE username = ?
    """, (username,))
    
    if cursor.rowcount > 0:
        print(f"✅ Enabled monitoring for @{username}")
    else:
        print(f"❌ Account @{username} not found")
    
    conn.commit()
    conn.close()

def disable_account(username):
    """Disable monitoring for an account"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    UPDATE monitored_accounts
    SET active = 0
    WHERE username = ?
    """, (username,))
    
    if cursor.rowcount > 0:
        print(f"✅ Disabled monitoring for @{username}")
    else:
        print(f"❌ Account @{username} not found")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Manage monitored social media accounts')
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add an account to monitor')
    add_parser.add_argument('username', help='Username to add')
    add_parser.add_argument('--platform', default='instagram', choices=['instagram'], 
                           help='Social media platform')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List monitored accounts')
    
    # Enable command
    enable_parser = subparsers.add_parser('enable', help='Enable monitoring for an account')
    enable_parser.add_argument('username', help='Username to enable')
    
    # Disable command
    disable_parser = subparsers.add_parser('disable', help='Disable monitoring for an account')
    disable_parser.add_argument('username', help='Username to disable')
    
    args = parser.parse_args()
    
    if args.command == 'add':
        add_account(args.username, args.platform)
    elif args.command == 'enable':
        enable_account(args.username)
    elif args.command == 'disable':
        disable_account(args.username)
    else:
        list_accounts()