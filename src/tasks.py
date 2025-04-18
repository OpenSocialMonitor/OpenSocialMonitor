import os
import time
import traceback
from celery import shared_task, states
from celery.exceptions import Ignore # To prevent retries for certain errors
from dotenv import load_dotenv

# Ensure env vars are loaded if this module is imported directly or early
load_dotenv()

# Import necessary components from your project
# Use absolute imports relative to the 'src' directory
from src.platforms.instagram import InstagramPlatform
from src.detection.indicators import calculate_bot_likelihood, detect_coordination
from src.database import db # Import the db instance from __init__.py

# --- Configuration (can be moved) ---
INTER_POST_SLEEP_SECONDS_TASK = 2 # Shorter sleep within task between posts? Adjust as needed.
DEFAULT_BOT_THRESHOLD_TASK = 0.65 # Match monitor.py or configure centrally

# --- Helper: Analyze Comments (Adapted for Task Context) ---
# This is similar to the helper in monitor.py, but potentially simplified
# as it runs within a task context for a single post.
def _analyze_comments_for_post_task(platform, comments, post_id, threshold):
    """Analyzes comments for a single post within a Celery task."""
    if not comments:
        return 0 # Bots detected

    print(f"    TASK: Analyzing {len(comments)} comments for Post ID: {post_id}")
    detected_bots_count = 0

    for comment in comments:
        comment_username = comment.get('username')
        comment_text = comment.get('text', '')
        comment_id = comment.get('id')

        if not comment_username or not comment_id or comment_username == platform.username:
            continue

        try:
            commenter_data = platform.get_user_info(comment_username)
            bot_likelihood, indicators = calculate_bot_likelihood(
                comment_username, comment_text, commenter_data
            )

            if bot_likelihood is not None and bot_likelihood >= threshold:
                detected_bots_count += 1
                indicator_keys = ', '.join(indicators.keys()) if indicators else 'None'
                print(f"      TASK: Bot detected: @{comment_username} ({bot_likelihood*100:.1f}%) Ind: [{indicator_keys}]")
                # Use the db instance method to add bot
                db.add_detected_bot(
                    username=comment_username, comment_id=comment_id, post_id=post_id,
                    bot_likelihood=bot_likelihood, comment_text=comment_text, indicators=indicators
                )
        except Exception as e:
            print(f"      TASK: Error analyzing comment by @{comment_username}: {e}")
            # Continue processing other comments

    # Coordination detection
    if len(comments) > 1:
        try:
            coordination_networks = detect_coordination(comments)
            if coordination_networks:
                print(f"    TASK: Coordination detected in post {post_id}:")
                # Log details if needed...
        except Exception as coord_err:
            print(f"    TASK: Error during coordination detection: {coord_err}")

    print(f"    TASK: Analysis complete for post {post_id}. Found {detected_bots_count} bots.")
    return detected_bots_count


# --- Celery Tasks ---

# Using shared_task allows tasks to be defined without importing the 'app' instance directly
# `bind=True` gives access to `self` (the task instance) for state updates and retries
@shared_task(bind=True, max_retries=2, default_retry_delay=30) # Retry twice, wait 30s
def process_instagram_post(self, post_url, monitored_account, platform_name='instagram',
                            max_comments=25, bot_threshold=DEFAULT_BOT_THRESHOLD_TASK):
    """
    Celery task to fetch comments for a single Instagram post and analyze them.
    """
    task_id = self.request.id
    print(f"TASK STARTING [{task_id}]: Processing post {post_url} for account {monitored_account}")
    self.update_state(state=states.STARTED, meta={'post_url': post_url})

    platform = None
    try:
        # Initialize platform connection within the task
        # Credentials should be loaded from environment variables via load_dotenv()
        print(f"  TASK [{task_id}]: Initializing Instagram connection...")
        platform = InstagramPlatform()
        if not platform.is_authenticated:
            print(f"  TASK [{task_id}]: Instagram login failed. Check credentials.")
            # Don't retry for login failure, raise Ignore
            raise Ignore("Instagram login failed, cannot proceed.")

        # --- Get Comments ---
        print(f"  TASK [{task_id}]: Fetching comments for {post_url} (max: {max_comments})...")
        post_id, comments = platform.get_post_comments(post_url, max_comments)
        if not post_id:
            print(f"  TASK [{task_id}]: Failed to retrieve post ID or comments. Skipping analysis.")
            # Mark as failure, but maybe don't retry if post is gone/private? Decide based on platform error.
            # For now, let it retry or fail permanently based on the exception from get_post_comments
            raise ValueError(f"Could not retrieve comments/ID for post {post_url}")

        print(f"  TASK [{task_id}]: Retrieved Post ID: {post_id} | Found {len(comments)} comments.")

        # --- Store Processed Post Record ---
        # Do this before analysis so we don't re-fetch if analysis fails and retries
        print(f"  TASK [{task_id}]: Recording post {post_id} as processed...")
        # Use the db instance method
        db.add_processed_post(post_id, post_url, monitored_account, platform_name)

        # --- Analyze Comments ---
        print(f"  TASK [{task_id}]: Starting comment analysis...")
        num_bots_found = _analyze_comments_for_post_task(platform, comments, post_id, bot_threshold)

        print(f"TASK SUCCESS [{task_id}]: Finished processing {post_url}. Found {num_bots_found} bots.")
        return {'post_url': post_url, 'post_id': post_id, 'comments_analyzed': len(comments), 'bots_found': num_bots_found}

    except Ignore as e:
        # Handle exceptions we don't want to retry (like login failure)
        print(f"TASK PERMANENT FAILURE (Ignored) [{task_id}]: {e}")
        self.update_state(state=states.FAILURE, meta={'post_url': post_url, 'exc_type': type(e).__name__, 'exc_message': str(e)})
        # Optional: Re-raise if you want Celery to log it explicitly as Ignore
        raise e
    except Exception as exc:
        # General exception handling: retry the task
        print(f"TASK RETRYING [{task_id}]: Error processing post {post_url}: {exc}")
        print(traceback.format_exc()) # Log traceback for debugging
        try:
            # Retry the task, Celery handles backoff based on default_retry_delay and max_retries
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            print(f"TASK PERMANENT FAILURE (Max Retries Exceeded) [{task_id}]: Error processing post {post_url}: {exc}")
            self.update_state(state=states.FAILURE, meta={'post_url': post_url, 'exc_type': type(exc).__name__, 'exc_message': str(exc)})
            # Optional: raise the original exception if needed elsewhere
            # raise exc
            return {'post_url': post_url, 'status': 'Failed after retries', 'error': str(exc)}


@shared_task(bind=True)
def process_account(self, username, platform_name='instagram',
                    max_posts=3, max_comments=25, bot_threshold=DEFAULT_BOT_THRESHOLD_TASK):
    """
    Celery task to fetch recent posts for an account and dispatch individual post processing tasks.
    """
    task_id = self.request.id
    print(f"ACCOUNT TASK STARTING [{task_id}]: Processing account @{username}")
    self.update_state(state=states.STARTED, meta={'username': username})

    platform = None
    post_urls = []
    try:
        print(f"  ACCOUNT TASK [{task_id}]: Initializing Instagram connection for @{username}...")
        platform = InstagramPlatform()
        if not platform.is_authenticated:
            print(f"  ACCOUNT TASK [{task_id}]: Instagram login failed. Cannot process account @{username}.")
            raise Ignore("Instagram login failed") # Don't retry account task if login fails

        # --- Get Posts ---
        print(f"  ACCOUNT TASK [{task_id}]: Fetching recent posts for @{username} (max: {max_posts})...")
        # Optional: Verify user exists first?
        # user_info = platform.get_user_info(username)
        # if not user_info: raise ValueError(f"Account @{username} not found.")

        post_urls = platform.get_user_posts(username, max_posts)
        if not post_urls:
            print(f"  ACCOUNT TASK [{task_id}]: No recent posts found for @{username}.")
            # Update last checked time even if no posts found
            # Use the db instance method
            db.update_last_checked(username)
            return {'username': username, 'status': 'No posts found'}

        print(f"  ACCOUNT TASK [{task_id}]: Found {len(post_urls)} posts for @{username}. Dispatching tasks...")

        # --- Dispatch Sub-Tasks ---
        dispatched_tasks = []
        for post_url in post_urls:
            # Check if post was *recently* processed? Maybe skip dispatch?
            # Requires checking db.processed_posts table with a timestamp condition

            # Dispatch a task for each post
            # Use .s() to create a signature, then .delay() or apply_async()
            task_sig = process_instagram_post.s(
                post_url=post_url,
                monitored_account=username,
                platform_name=platform_name,
                max_comments=max_comments,
                bot_threshold=bot_threshold
            )
            task_result = task_sig.delay() # Send task to the queue
            print(f"    -> Dispatched task {task_result.id} for post: {post_url}")
            dispatched_tasks.append(task_result.id)
            # Optional: Short sleep between dispatches to avoid overwhelming broker?
            # time.sleep(0.1)

        # Update last checked time for the account
        # Use the db instance method
        db.update_last_checked(username)

        print(f"ACCOUNT TASK SUCCESS [{task_id}]: Finished dispatching {len(dispatched_tasks)} post tasks for @{username}.")
        return {'username': username, 'dispatched_post_task_ids': dispatched_tasks}

    except Ignore as e:
        print(f"ACCOUNT TASK PERMANENT FAILURE (Ignored) [{task_id}]: {e}")
        self.update_state(state=states.FAILURE, meta={'username': username, 'exc_type': type(e).__name__, 'exc_message': str(e)})
        raise e
    except Exception as exc:
        # Should this task retry? Maybe not, if fetching posts fails consistently.
        print(f"ACCOUNT TASK PERMANENT FAILURE [{task_id}]: Error processing account @{username}: {exc}")
        print(traceback.format_exc())
        self.update_state(state=states.FAILURE, meta={'username': username, 'exc_type': type(exc).__name__, 'exc_message': str(exc)})
        # Don't retry by default for account-level fetch errors
        return {'username': username, 'status': 'Failed', 'error': str(exc)}
