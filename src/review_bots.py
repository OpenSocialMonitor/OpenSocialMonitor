import argparse
import sys
import os
import random
from dotenv import load_dotenv

# Load environment variables from .env file FIRST
load_dotenv()

# Now import other modules
# Import the db instance from the database package's __init__.py
from src.database import db
# Import the platform class - it should handle its own auth using os.environ
from src.platforms.instagram import InstagramPlatform

def list_pending_bots():
    """List detected bots that are pending review (not approved/sent or rejected)."""
    # Use the 'get_pending_bots' method from our 'db' instance
    bots = db.get_pending_bots()

    if not bots:
        print("✅ No pending bot warnings to review.")
    else:
        print("\n--- Pending Bot Warnings ---")
        print("-" * 95) # Adjusted width
        print(f"{'ID':<5} {'Username':<25} {'Likelihood':<12} {'Detected On':<25} {'Comment Snippet'}")
        print("-" * 95)
        for bot_id, username, likelihood, comment, post_url, detected in bots:
            short_comment = comment[:40] + "..." if comment and len(comment) > 40 else (comment or "[No Text]")
            likelihood_str = f"{likelihood*100:.1f}%" if likelihood is not None else "N/A"
            detected_str = detected if detected else "Unknown Date"
            print(f"{bot_id:<5} {username:<25} {likelihood_str:<12} {detected_str:<25.25} {short_comment}")
        print("-" * 95)
        print("\nCommands:")
        print("  python -m src.review_bots view <id>    - View details for a specific detection")
        print("  python -m src.review_bots approve <id> - Approve and send warning comment")
        print("  python -m src.review_bots reject <id>  - Mark detection as incorrect (not a bot)")

def view_bot_details(bot_id):
    """View detailed information about a specific bot detection."""
    # Use the 'get_bot_details' method from our 'db' instance
    # Returns tuple: (username, likelihood, ..., comment_id, post_id, indicators) or None
    result = db.get_bot_details(bot_id)

    if not result:
        print(f"❌ Error: No bot detection found with ID {bot_id}.")
    else:
        # Unpack all fields returned by get_bot_details
        username, likelihood, comment, post_url, detected, \
        warning_sent, warning_approved, comment_id, post_id, indicators = result

        print("\n--- Bot Detection Details ---")
        print(f"Detection ID: {bot_id}")
        print("-" * 50)
        print(f"Username:         @{username}")
        print(f"Bot Likelihood:   {likelihood*100:.1f}%" if likelihood is not None else "N/A")
        print(f"Detected On:      {detected}")
        print(f"Origin Post URL:  {post_url}")
        print(f"Origin Post ID:   {post_id}")
        print(f"Origin Comment ID:{comment_id}")
        print(f"Detected Indicators: {indicators or 'None'}") # Display indicators
        print("\nComment Text:")
        print("-" * 50)
        print(comment if comment else "[No comment text stored]")
        print("-" * 50)

        # Determine status based on flags
        if warning_sent == 1 and warning_approved == 1:
            print("Status: ✅ Warning Sent")
        elif warning_sent == 0 and warning_approved == 0:
             # Could be pending or rejected, let's assume rejected if approved=0
             print("Status: ❌ Rejected (Marked as not a bot)")
        elif warning_sent == 0 and warning_approved == 1:
             print("Status: ⚠️ Approved but Sending Failed (or Pending Send)")
        else: # warning_sent=1, warning_approved=0 should ideally not happen
             print("Status: ❓ Inconsistent State (Sent=1, Approved=0)")

        # Show available actions only if pending/failed send
        if warning_sent == 0:
             print("\nActions:")
             print(f"  Approve & Send Warning: python -m src.review_bots approve {bot_id}")
             print(f"  Reject Detection:       python -m src.review_bots reject {bot_id}")


def approve_and_send_warning(bot_id):
    """Approve a bot detection and attempt to send a warning comment via Instagram."""
    print(f"\n--- Approving and Sending Warning for Bot ID: {bot_id} ---")
    # Get details, ensure it's actionable
    # Returns tuple: (username, ..., warning_sent, warning_approved, comment_id, post_id, indicators) or None
    result = db.get_bot_details(bot_id)

    if not result:
        print(f"❌ Error: No bot detection found with ID {bot_id}.")
        return

    # Unpack needed fields
    username, _, _, post_url, _, warning_sent, warning_approved, comment_id, post_id, _ = result

    # Check status before proceeding
    if warning_sent == 1 and warning_approved == 1:
        print(f"✅ Info: Warning for bot ID {bot_id} (@{username}) has already been sent.")
        return
    # Allow re-sending if approved but sending failed previously (sent=0, approved=1)
    if warning_sent == 0 and warning_approved == 0: # If rejected
        print(f"ℹ️ Info: This detection (ID: {bot_id}) was previously marked as rejected. Re-approving.")
        # Proceed, will set approved=1 later

    if not comment_id:
        print(f"❌ Error: Cannot send warning for Bot ID {bot_id}. Original comment ID is missing.")
        # Option: Mark as approved but not sent
        # db.update_bot_warning_status(bot_id, sent=False, approved=True)
        # print("Marked detection as approved, but cannot send warning (missing comment ID).")
        return

    print(f"  Target User: @{username}")
    print(f"  Target Post: {post_url} (Post ID: {post_id})")
    print(f"  Replying to Comment ID: {comment_id}")

    # Confirmation step
    confirm = input("❓ Proceed with sending the warning comment? (y/n): ")
    if confirm.lower() != 'y':
        print("🚫 Action aborted by user.")
        return

    # Initialize Instagram client - needs loaded env vars
    print("  Initializing Instagram connection...")
    platform = None
    try:
        # Assumes InstagramPlatform uses env vars loaded by load_dotenv()
        platform = InstagramPlatform()
        if not platform.is_authenticated:
            print("❌ Error: Failed to log in to Instagram. Check credentials in .env file.")
            # Cannot proceed without login
            # Update DB to approved=1, sent=0 to indicate attempt failed?
            db.update_bot_warning_status(bot_id, sent=False, approved=True)
            print("  Marked detection as approved, but sending failed (login error).")
            return
        print("  ✅ Instagram login successful.")
    except Exception as e:
        print(f"❌ Error initializing Instagram platform: {e}")
        # Update DB to approved=1, sent=0 ?
        db.update_bot_warning_status(bot_id, sent=False, approved=True)
        print("  Marked detection as approved, but sending failed (platform init error).")
        return

    # Define warning messages (Consider making these configurable externally)
    warning_messages = [
        f"⚠️ Heads up! Our analysis suggests @{username} might exhibit bot-like behavior. Engage critically. #OpenSocialMonitor",
        f"🤖 Bot alert? Activity patterns associated with @{username} resemble automation. Verify info independently. #OpenSocialMonitor",
        f"🔍 Transparency Note: Analysis indicates @{username} may be automated. Interact mindfully. #OpenSocialMonitor",
        f"📊 Interaction patterns suggest @{username} could be automated. Shared for awareness. #OpenSocialMonitor",
    ]
    warning_text = random.choice(warning_messages)
    print(f"  Selected warning message:\n  \"{warning_text}\"")

    # === Actually Post the Warning ===
    print("  Posting warning comment via Instagram API...")
    success = False
    try:
        # Assume platform has 'post_reply_comment' method
        # Adapt if method name/args differ in your src/platforms/instagram.py
        success = platform.post_reply_comment(post_url=post_url,
                                              target_comment_id=comment_id,
                                              text=warning_text)
    except Exception as e:
        print(f"❌ Error during Instagram API call for posting comment: {e}")
        success = False # Ensure success is false on exception

    # === Update Database Based on Outcome ===
    if success:
        print("✅ Warning comment posted successfully on Instagram.")
        print("  Updating database status to 'sent' and 'approved'...")
        db_updated = db.update_bot_warning_status(bot_id, sent=True, approved=True)
        if not db_updated:
             print("⚠️ Error: Failed to update database status after successfully sending warning.")
    else:
        print("❌ Error: Failed to post warning comment via Instagram API (platform method returned failure or exception occurred).")
        print("  Updating database status to 'approved' but 'not sent'...")
        db_updated = db.update_bot_warning_status(bot_id, sent=False, approved=True)
        if not db_updated:
            print("⚠️ Error: Failed to update database status after send failure.")


def reject_detection(bot_id):
    """Marks a bot detection as incorrect (not a bot) in the database."""
    print(f"\n--- Rejecting Bot Detection ID: {bot_id} ---")
    # Check if it exists first
    details = db.get_bot_details(bot_id)
    if not details:
         print(f"❌ Error: No bot detection found with ID {bot_id}.")
         return

    # Update database status: warning_sent = 0, warning_approved = 0
    # This signifies it's been reviewed and deemed not a bot
    print("  Updating database status to 'rejected' (approved=0, sent=0)...")
    # Use the 'update_bot_warning_status' method from our 'db' instance
    db_updated = db.update_bot_warning_status(bot_id, sent=False, approved=False)
    if db_updated:
        print("✅ Database status updated successfully.")
    else:
        # Should not happen if get_bot_details found it
        print(f"❌ Error: Failed to update database status for rejection.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Review and manage detected bots. Run without arguments to list pending bots.',
        formatter_class=argparse.RawTextHelpFormatter # Nicer help text
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # View command
    view_parser = subparsers.add_parser('view', help='View details of a specific detected bot')
    view_parser.add_argument('id', type=int, help='Bot ID to view')

    # Approve command
    approve_parser = subparsers.add_parser('approve', help='Approve and attempt to send warning for a detected bot')
    approve_parser.add_argument('id', type=int, help='Bot ID to approve and send warning for')

    # Reject command
    reject_parser = subparsers.add_parser('reject', help='Mark a detection as incorrect (not a bot)')
    reject_parser.add_argument('id', type=int, help='Bot ID to reject')

    # List command (explicitly, though it's the default)
    list_parser = subparsers.add_parser('list', help='List pending bot warnings (default action)')

    args = parser.parse_args()

    # Execute command or list if no command given
    if args.command == 'view':
        view_bot_details(args.id)
    elif args.command == 'approve':
        approve_and_send_warning(args.id)
    elif args.command == 'reject':
        reject_detection(args.id)
    elif args.command == 'list':
        list_pending_bots()
    else:
        # Default action: list pending bots
        list_pending_bots()