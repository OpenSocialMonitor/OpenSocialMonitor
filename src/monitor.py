"""
Main monitoring script for OpenSocialMonitor

This script checks monitored accounts for new posts and analyzes them for bot activity.
"""

import os
import time
import argparse
import sys
from datetime import datetime

# Import components from our modular structure
from src.platforms.instagram import InstagramPlatform
from src.detection.indicators import calculate_bot_likelihood, detect_coordination
from src.database import db

def check_for_new_posts(platform_name='instagram', max_posts_per_account=3, max_comments=15, bot_threshold=0.6):
    """
    Check monitored accounts for new posts and analyze them for bot activity
    
    Args:
        platform_name (str): Platform to monitor ('instagram' is currently the only supported option)
        max_posts_per_account (int): Maximum number of recent posts to check per account
        max_comments (int): Maximum number of comments to analyze per post
        bot_threshold (float): Minimum likelihood score to consider an account a bot (0-1)
    """
    print(f"OpenSocialMonitor - Starting monitoring process")
    print(f"Platform: {platform_name}")
    print(f"Bot detection threshold: {bot_threshold}")
    
    # Initialize the platform connector
    if platform_name.lower() == 'instagram':
        platform = InstagramPlatform()
        if not platform.login():
            print("Failed to log in to Instagram. Check your credentials.")
            return
    else:
        print(f"Unsupported platform: {platform_name}")
        return
    
    # Get accounts to monitor
    accounts = db.get_monitored_accounts()
    
    if not accounts:
        print("No accounts to monitor. Add accounts using add_account.py")
        return
    
    print(f"\nChecking {len(accounts)} accounts for new posts...")
    
    # Track overall statistics
    total_posts_checked = 0
    total_posts_new = 0
    total_comments_analyzed = 0
    total_bots_detected = 0
    
    # Process each monitored account
    for username, _, last_checked in accounts:
        print(f"\n➤ Checking account: @{username}")
        
        try:
            # Get user info
            user_info = platform.get_user_info(username)
            if not user_info:
                print(f"  ✗ Could not retrieve information for @{username}")
                continue
            
            print(f"  ✓ Found account: {user_info.get('full_name', username)} ({user_info.get('follower_count', 0)} followers)")
            
            # Get recent posts
            post_urls = platform.get_user_posts(username, max_posts_per_account)
            print(f"  ✓ Retrieved {len(post_urls)} recent posts")
            
            # Process each post
            for post_url in post_urls:
                print(f"\n  ➤ Checking post: {post_url}")
                total_posts_checked += 1
                
                # Extract post ID and get comments
                post_id, comments = platform.get_post_comments(post_url, max_comments)
                if not post_id:
                    print(f"    ✗ Could not retrieve comments for {post_url}")
                    continue
                
                # Check if we've already processed this post
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM processed_posts WHERE post_id = ?", (post_id,))
                if cursor.fetchone():
                    print(f"    ✓ Already processed post (ID: {post_id})")
                    conn.close()
                    continue
                
                conn.close()
                
                # New post found
                print(f"    ✓ Found new post (ID: {post_id})")
                total_posts_new += 1
                
                # Store this post in database
                db.add_processed_post(post_id, post_url, username, platform_name)
                
                # Analyze comments
                print(f"    ➤ Analyzing {len(comments)} comments")
                total_comments_analyzed += len(comments)
                
                # Track detected bots for this post
                detected_bots = []
                
                # Process each comment
                for comment in comments:
                    # Skip our own comments
                    if comment['username'] == platform.username:
                        continue
                    
                    # Get user data for better analysis
                    commenter_data = platform.get_user_info(comment['username'])
                    
                    # Calculate bot likelihood
                    bot_likelihood, indicators = calculate_bot_likelihood(
                        comment['username'],
                        comment['text'],
                        commenter_data
                    )
                    
                    # If likely a bot, add to detection list
                    if bot_likelihood >= bot_threshold:
                        detected_bots.append({
                            'username': comment['username'],
                            'comment_text': comment['text'],
                            'comment_id': comment['id'],
                            'bot_likelihood': bot_likelihood,
                            'indicators': indicators
                        })
                        
                        # Store bot detection
                        db.add_detected_bot(
                            username=comment['username'],
                            comment_id=comment['id'],
                            post_id=post_id,
                            bot_likelihood=bot_likelihood,
                            comment_text=comment['text']
                        )
                        
                        # Print information about the detected bot
                        print(f"    ⚠️  Detected bot: @{comment['username']} ({bot_likelihood*100:.1f}%)")
                        print(f"       Comment: \"{comment['text'][:50]}...\"")
                        print(f"       Indicators: {', '.join(indicators.keys())}")
                
                # Update bot count
                total_bots_detected += len(detected_bots)
                
                # Check for coordination
                coordination = detect_coordination(comments)
                if coordination:
                    print(f"\n    ⚠️  Detected coordinated activity:")
                    for network in coordination:
                        print(f"       Users: {', '.join(network['users'])}")
                        print(f"       Message: \"{network['text'][:50]}...\"")
                        print(f"       Confidence: {network['confidence']*100:.1f}%")
                
                print(f"    ✓ Found {len(detected_bots)} potential bots in this post")
                
                # Sleep to avoid rate limiting
                time.sleep(3)
            
        except Exception as e:
            print(f"  ✗ Error processing account @{username}: {e}")
        
        # Sleep between accounts to avoid rate limiting
        time.sleep(5)
    
    # Print summary
    print("\n" + "="*50)
    print("MONITORING SUMMARY:")
    print(f"Total accounts checked: {len(accounts)}")
    print(f"Total posts checked: {total_posts_checked}")
    print(f"New posts found: {total_posts_new}")
    print(f"Comments analyzed: {total_comments_analyzed}")
    print(f"Potential bots detected: {total_bots_detected}")
    print("="*50)
    
    print("\nScan complete. Run 'python review_bots.py' to review detected bots.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Monitor social media for bot activity')
    parser.add_argument('--platform', default='instagram', choices=['instagram'], 
                       help='Social media platform to monitor')
    parser.add_argument('--posts', type=int, default=3, 
                       help='Maximum number of recent posts to check per account')
    parser.add_argument('--comments', type=int, default=15,
                       help='Maximum number of comments to analyze per post')
    parser.add_argument('--threshold', type=float, default=0.6,
                       help='Bot likelihood threshold (0-1)')
    parser.add_argument('--post', help='URL of a specific post to monitor')
    parser.add_argument('--account', help='Username of a specific account to monitor')
    
    args = parser.parse_args()
    
    # If a specific post is provided, monitor just that post
    if args.post:
        print(f"Monitoring specific post: {args.post}")
        # Initialize platform
        if args.platform.lower() == 'instagram':
            platform = InstagramPlatform()
            if not platform.login():
                print("Failed to log in to Instagram. Check your credentials.")
                sys.exit(1)

            # Get comments from the post
            post_id, comments = platform.get_post_comments(args.post, args.comments)
            if not post_id:
                print(f"Could not retrieve comments from {args.post}")
                sys.exit(1)
                
            print(f"Analyzing {len(comments)} comments")
            
            # Add the post to database
            db.add_processed_post(post_id, args.post, 'unknown_user', args.platform)
            
            # Track detected bots
            detected_bots = []
            
            # Process each comment to detect bots
            print("\nCOMMENT ANALYSIS:")
            print("-" * 50)
            
            for comment in comments:
                username = comment['username']
                comment_text = comment['text']
                comment_id = comment['id']
                
                # Skip if it's our own comment
                if username == platform.username:
                    continue
                    
                # Get user data if available
                user_data = platform.get_user_info(username)
                
                # Calculate bot likelihood
                bot_likelihood, indicators = calculate_bot_likelihood(
                    username, 
                    comment_text,
                    user_data
                )
                
                # Print analysis for this comment
                short_text = comment_text[:40] + "..." if len(comment_text) > 40 else comment_text
                print(f"User: {username}")
                print(f"Comment: {short_text}")
                print(f"Bot likelihood: {bot_likelihood*100:.1f}%")
                
                if indicators:
                    print(f"Indicators: {', '.join(indicators.keys())}")
                else:
                    print("No bot indicators detected")
                    
                print("-" * 50)
                
                # If likely a bot, store in database
                if bot_likelihood >= args.threshold:
                    detected_bots.append({
                        'username': username,
                        'comment_text': comment_text,
                        'comment_id': comment_id,
                        'bot_likelihood': bot_likelihood,
                        'indicators': indicators
                    })
                    
                    # Store in database
                    db.add_detected_bot(
                        username=username,
                        comment_id=comment_id,
                        post_id=post_id,
                        bot_likelihood=bot_likelihood,
                        comment_text=comment_text
                    )
            
            # Check for coordination
            coordination = detect_coordination(comments)
            
            # Print summary
            print("\nANALYSIS SUMMARY:")
            print(f"Total comments analyzed: {len(comments)}")
            print(f"Potential bots detected: {len(detected_bots)}")
            
            if detected_bots:
                print("\nDETECTED BOTS:")
                for bot in detected_bots:
                    print(f"- @{bot['username']} ({bot['bot_likelihood']*100:.1f}%)")
            
            if coordination:
                print("\nCOORDINATED ACTIVITY DETECTED:")
                for network in coordination:
                    print(f"- Users: {', '.join(network['users'])}")
                    print(f"  Text: \"{network['text'][:50]}...\"")
                    print(f"  Confidence: {network['confidence']*100:.1f}%")
            
            print("\nTo review these detections later, run: python -m src.review_bots")
            
    elif args.account:
        print(f"Monitoring account: @{args.account}")
        # Initialize platform
        if args.platform.lower() == 'instagram':
            platform = InstagramPlatform()
            if not platform.login():
                print("Failed to log in to Instagram. Check your credentials.")
                sys.exit(1)

            # Get recent posts from the account
            post_urls = platform.get_user_posts(args.account, args.posts)
            
            if not post_urls:
                print(f"Could not retrieve posts from @{args.account}")
                sys.exit(1)
                
            print(f"Found {len(post_urls)} posts to analyze")
            
            # Process each post
            for i, post_url in enumerate(post_urls, 1):
                print(f"\nAnalyzing post {i}/{len(post_urls)}: {post_url}")
                post_id, comments = platform.get_post_comments(post_url, args.comments)
                
                if not post_id:
                    print(f"Could not retrieve comments from {post_url}")
                    continue
                    
                print(f"Found {len(comments)} comments to analyze")
                
                # Add the post to database
                db.add_processed_post(post_id, post_url, args.account, args.platform)
                
                # Track detected bots
                detected_bots = []
                
                # Process each comment to detect bots
                print("\nCOMMENT ANALYSIS:")
                print("-" * 50)
                
                for comment in comments:
                    try:
                        username = comment['username']
                        comment_text = comment['text']
                        comment_id = comment['id']
                        
                        # Skip if it's our own comment
                        if username == platform.username:
                            continue
                            
                        # Get user data if available
                        user_data = platform.get_user_info(username)
                        
                        # Calculate bot likelihood
                        bot_likelihood, indicators = calculate_bot_likelihood(
                            username, 
                            comment_text,
                            user_data
                        )
                        
                        # Print analysis for this comment
                        short_text = comment_text[:40] + "..." if len(comment_text) > 40 else comment_text
                        print(f"User: {username}")
                        print(f"Comment: {short_text}")
                        print(f"Bot likelihood: {bot_likelihood*100:.1f}%")
                        
                        if indicators:
                            print(f"Indicators: {', '.join(indicators.keys())}")
                        else:
                            print("No bot indicators detected")
                            
                        print("-" * 50)
                        
                        # If likely a bot, store in database
                        if bot_likelihood >= args.threshold:
                            detected_bots.append({
                                'username': username,
                                'comment_text': comment_text,
                                'comment_id': comment_id,
                                'bot_likelihood': bot_likelihood,
                                'indicators': indicators
                            })
                            
                            # Store in database
                            db.add_detected_bot(
                                username=username,
                                comment_id=comment_id,
                                post_id=post_id,
                                bot_likelihood=bot_likelihood,
                                comment_text=comment_text
                            )
                    except Exception as e:
                        print(f"Error processing comment: {e}")