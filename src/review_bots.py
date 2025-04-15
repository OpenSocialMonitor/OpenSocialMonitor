"""
Review and approve detected bots

This script allows you to view and manage bot detections
and send warning comments when appropriate.
"""

import argparse
import sys
from src.platforms.instagram import InstagramPlatform
from src.database import db

def list_pending_bots():
    """List all detected bots pending approval"""
    bots = db.get_pending_bots()
    
    if not bots:
        print("No pending bot warnings to review")
    else:
        print("\nPending Bot Warnings:")
        print("-" * 90)
        print(f"{'ID':<5} {'Username':<20} {'Likelihood':<12} {'Detected':<20} {'Comment'}")
        print("-" * 90)
        
        for bot_id, username, likelihood, comment, post_url, detected in bots:
            # Truncate comment if needed
            short_comment = comment[:40] + "..." if len(comment) > 40 else comment
            print(f"{bot_id:<5} {username:<20} {likelihood*100:<12.1f}% {detected:<20} {short_comment}")
        
        print("\nCommands:")
        print("  python review_bots.py view [id]    - View details for a specific bot")
        print("  python review_bots.py approve [id] - Approve and send warning")

def view_bot_details(bot_id):
    """View detailed information about a detected bot"""
    result = db.get_bot_details(bot_id)
    
    if not result:
        print(f"No bot found with ID {bot_id}")
    else:
        username, likelihood, comment, post_url, detected, warning_sent, comment_id, post_id = result
        
        print("\nBot Details:")
        print("-" * 50)
        print(f"Username: @{username}")
        print(f"Bot Likelihood: {likelihood*100:.1f}%")
        print(f"Detected on: {detected}")
        print(f"Post URL: {post_url}")
        print(f"Comment:")
        print("-" * 50)
        print(comment)
        print("-" * 50)
        
        if warning_sent:
            print("⚠️ Warning has already been sent")
        else:
            print("To approve warning: python review_bots.py approve", bot_id)

def approve_warning(bot_id):
    """Approve and send a warning for a detected bot"""
    # Get the bot information
    result = db.get_bot_details(bot_id)
    
    if not result or result[5]:  # If bot not found or warning already sent
        print(f"No pending warning found with ID {bot_id}")
        return
    
    username, likelihood, comment, post_url, detected, warning_sent, comment_id, post_id = result
    
    print(f"Preparing to send warning for bot ID {bot_id}...")
    print(f"Username: @{username}")
    print(f"Post: {post_url}")
    
    # Initialize Instagram client
    platform = InstagramPlatform()
    print("Logging in to Instagram...")
    if not platform.login():
        print("Failed to log in to Instagram. Check your credentials.")
        return
    
    print("Posting warning comment...")
    # Post the warning comment
    success = platform.post_warning_comment(post_url, username, comment_id)
    
    if success:
        # Update database
        db.update_bot_warning_status(bot_id)
        print("✅ Warning successfully sent")
        print("✅ Database updated")
    else:
        print("❌ Failed to post warning comment")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Review and manage detected bots')
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # View command
    view_parser = subparsers.add_parser('view', help='View details of a detected bot')
    view_parser.add_argument('id', type=int, help='Bot ID to view')
    
    # Approve command
    approve_parser = subparsers.add_parser('approve', help='Approve and send warning for a detected bot')
    approve_parser.add_argument('id', type=int, help='Bot ID to approve')
    
    args = parser.parse_args()
    
    if args.command == 'view':
        view_bot_details(args.id)
    elif args.command == 'approve':
        approve_warning(args.id)
    else:
        list_pending_bots()