# This script acts as a dispatcher, sending tasks to Celery workers.
import os
import time
import argparse
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file FIRST
load_dotenv()

# Import database access and tasks
from src.database import db # Uses DatabaseManager instance
from src.tasks import process_account, process_instagram_post # Import task functions

# --- Configuration Constants ---
# These defaults are passed TO the tasks if not overridden by args
DEFAULT_MAX_POSTS_PER_ACCOUNT = 3
DEFAULT_MAX_COMMENTS_PER_POST = 25
DEFAULT_BOT_THRESHOLD = 0.65
PLATFORM_NAME = 'instagram'

# --- Main Dispatching Logic ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='OpenSocialMonitor Dispatcher: Send monitoring tasks to Celery workers.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--platform', default=PLATFORM_NAME, choices=[PLATFORM_NAME],
                       help='Social media platform (only Instagram currently)')
    parser.add_argument('--posts', type=int, default=DEFAULT_MAX_POSTS_PER_ACCOUNT, metavar='N',
                       help='Max recent posts tasks should check per account')
    parser.add_argument('--comments', type=int, default=DEFAULT_MAX_COMMENTS_PER_POST, metavar='N',
                       help='Max comments tasks should analyze per post')
    parser.add_argument('--threshold', type=float, default=DEFAULT_BOT_THRESHOLD, metavar='0.X',
                       help='Bot likelihood threshold tasks should use (0.0 to 1.0)')

    target_group = parser.add_mutually_exclusive_group()
    target_group.add_argument('--post', metavar='URL',
                              help='Dispatch a task for a single specific post URL')
    target_group.add_argument('--account', metavar='USERNAME',
                              help='Dispatch a task for a single specific account')
    # If neither --post nor --account is given, dispatch tasks for all active accounts

    args = parser.parse_args()

    # Validate threshold
    if not 0.0 <= args.threshold <= 1.0:
        print("Error: Threshold must be between 0.0 and 1.0")
        sys.exit(1)

    start_time = time.time()
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] OpenSocialMonitor Dispatcher Starting...")
    print(f"Mode: {'Single Post Task' if args.post else ('Single Account Task' if args.account else 'All Active Accounts Tasks')}")

    # --- Initialization Check (Optional but good) ---
    # try:
    #     print("Checking database connection...")
    #     # Accessing db implicitly checks connection via __init__/_initialize_database
    #     _ = db.get_connection() # Simple way to trigger initialization/connection check
    #     if _ is None: raise ConnectionError("Failed to get DB connection")
    #     _.close()
    #     print("Database connection check OK.")
    # except Exception as init_err:
    #     print(f"\n❌ FATAL: Initialization check failed: {init_err}")
    #     sys.exit(1)

    # --- Dispatch Tasks ---
    dispatched_count = 0
    total_accounts_to_process = 0
    try:
        if args.post:
            print(f"Dispatching task to process post: {args.post}")
            # Call .delay() on the task function to send it to the queue
            task_result = process_instagram_post.delay(
                post_url=args.post,
                monitored_account='single_post_run', # Indicate origin
                platform_name=args.platform,
                max_comments=args.comments,
                bot_threshold=args.threshold
            )
            print(f"  -> Task ID: {task_result.id}")
            dispatched_count = 1

        elif args.account:
            print(f"Dispatching task to process account: @{args.account}")
            task_result = process_account.delay(
                username=args.account,
                platform_name=args.platform,
                max_posts=args.posts,
                max_comments=args.comments,
                bot_threshold=args.threshold
            )
            print(f"  -> Task ID: {task_result.id}")
            dispatched_count = 1 # This task will dispatch sub-tasks

        else:
            print("Fetching active accounts to dispatch tasks...")
            # Use the db instance method
            accounts_to_monitor = db.get_monitored_accounts(active_only=True)
            total_accounts_to_process = len(accounts_to_monitor)
            if not accounts_to_monitor:
                print("No active accounts found to monitor.")
            else:
                print(f"Dispatching tasks for {total_accounts_to_process} active accounts...")
                for i, (username, _, _) in enumerate(accounts_to_monitor):
                    print(f"  Dispatching task {i+1}/{total_accounts_to_process} for @{username}...")
                    task_result = process_account.delay(
                        username=username,
                        platform_name=args.platform,
                        max_posts=args.posts,
                        max_comments=args.comments,
                        bot_threshold=args.threshold
                    )
                    print(f"    -> Task ID: {task_result.id}")
                    dispatched_count += 1
                    # Optional: Add a small delay between dispatches?
                    # time.sleep(0.05) # 50ms delay

    except ImportError as e:
         print(f"\n❌ ERROR: Failed to import tasks. Is Celery running or configured correctly? Error: {e}")
         import traceback
         traceback.print_exc()
    except Exception as dispatch_err:
        print(f"\n❌ ERROR during task dispatch: {dispatch_err}")
        import traceback
        traceback.print_exc()

    finally:
        end_time = time.time()
        duration = end_time - start_time
        print("\n" + "="*60)
        print("Dispatcher Finished")
        print(f"Duration: {duration:.2f} seconds")
        if not args.post and not args.account:
            print(f"Attempted to dispatch tasks for {total_accounts_to_process} accounts.")
        print(f"Actual tasks dispatched by this script: {dispatched_count}")
        print("Note: 'process_account' tasks dispatch sub-tasks for posts.")
        print("\nRun a Celery worker in a separate terminal to process these tasks:")
        print("  celery -A celery_app worker --loglevel=INFO [-P solo]")
        print("Monitor worker logs and 'python -m src.review_bots' for results.")
        print("="*60)
