"""
Instagram platform connector for social media monitoring

This module provides a clean interface for interacting with the Instagram API,
handling authentication, data retrieval, and interaction functionality.
"""

import os
import time
import random
import statistics
import re
from datetime import datetime, timedelta
from instagrapi import Client
from dotenv import load_dotenv

class InstagramPlatform:
    """Instagram platform implementation using instagrapi"""
    
    def __init__(self):
        """Initialize Instagram connector"""
        # Load environment variables
        load_dotenv()
        
        self.client = Client()
        self.username = os.getenv('INSTAGRAM_USERNAME')
        self.password = os.getenv('INSTAGRAM_PASSWORD')
        self.is_logged_in = False
        self.name = "Instagram"  # For testing purposes
    
    def login(self):
        """
        Login to Instagram API
        
        Returns:
            bool: Whether login was successful
        """
        try:
            self.client.login(self.username, self.password)
            print("Successfully logged in to Instagram")
            self.is_logged_in = True
            return True
        except Exception as e:
            print(f"Instagram login failed: {e}")
            self.is_logged_in = False
            return False
    
    def get_user_info(self, username):
        """
        Get detailed information about an Instagram user
        
        Args:
            username (str): Instagram username to analyze
            
        Returns:
            dict: User information or None if failed
        """
        if not self.is_logged_in and not self.login():
            return None
        
        try:
            # Add small delay to avoid rate limiting
            time.sleep(random.uniform(1, 2))
            
            # Get user info
            user_info = self.client.user_info_by_username(username)
            
            # Format the results in a platform-agnostic way
            return {
                'platform': 'instagram',
                'username': username,
                'user_id': user_info.pk,
                'full_name': user_info.full_name,
                'follower_count': user_info.follower_count,
                'following_count': user_info.following_count,
                'media_count': user_info.media_count,
                'is_verified': user_info.is_verified,
                'is_private': user_info.is_private,
                'bio': user_info.biography,
                'has_profile_pic': user_info.profile_pic_url != "",
                'url': f"https://instagram.com/{username}/"
            }
        except Exception as e:
            print(f"Error getting user info for {username}: {e}")
            return None
    
    def get_user_media(self, username, amount=20):
        """
        Get recent media posts from a user
        
        Args:
            username (str): Instagram username
            amount (int): Number of recent posts to retrieve
            
        Returns:
            list: List of media items or empty list if failed
        """
        if not self.is_logged_in and not self.login():
            return []
        
        try:
            # Get user info first to get user ID
            user_info = self.client.user_info_by_username(username)
            
            # Try to get user media with error handling
            try:
                medias = self.client.user_medias(user_info.pk, amount)
            except KeyError as e:
                print(f"Using alternative method to get media due to API change")
                # Try alternative method if available
                try:
                    medias = self.client.user_medias_v1(user_info.pk, amount)
                except Exception as e2:
                    print(f"Alternative method failed: {e2}")
                    # Last resort - try to get user feed posts
                    try:
                        medias = self.client.user_feed(user_info.pk, amount)
                    except Exception as e3:
                        print(f"All methods to get user media failed: {e3}")
                        return []
            
            # Format results
            formatted_media = []
            for media in medias:
                formatted_media.append({
                    'id': media.id,
                    'code': media.code,
                    'url': f"https://www.instagram.com/p/{media.code}/",
                    'timestamp': media.taken_at,
                    'like_count': media.like_count,
                    'comment_count': media.comment_count
                })
            
            return formatted_media
        except Exception as e:
            print(f"Error getting media for {username}: {e}")
            return []
    
    def get_post_comments(self, post_url, limit=20):
        """
        Get comments from an Instagram post
        
        Args:
            post_url (str): URL of the Instagram post
            limit (int): Maximum number of comments to retrieve
            
        Returns:
            tuple: (post_id, list of comments) or (None, []) if failed
        """
        if not self.is_logged_in and not self.login():
            return None, []
        
        try:
            # Extract media ID from URL
            try:
                media_pk = self.client.media_pk_from_url(post_url)
            except Exception as e:
                print(f"Error extracting media ID: {e}")
                # If the URL doesn't work, try to extract code from URL and use that
                code_match = re.search(r'instagram\.com/p/([^/]+)', post_url)
                if code_match:
                    media_code = code_match.group(1)
                    try:
                        media_pk = self.client.media_pk_from_code(media_code)
                    except Exception as e:
                        print(f"Error with alternative method: {e}")
                        return None, []
                else:
                    return None, []
            
            # Get comments
            try:
                comments = self.client.media_comments(media_pk, limit)
                
                # Format the results
                formatted_comments = []
                for comment in comments:
                    formatted_comments.append({
                        'id': str(comment.pk),  # Ensure ID is string
                        'user_id': str(comment.user.pk),  # Ensure ID is string
                        'username': comment.user.username,
                        'text': comment.text,
                        'created_at': comment.created_at_utc.isoformat() if comment.created_at_utc else None,
                    })
                
                return str(media_pk), formatted_comments
            except Exception as e:
                print(f"Error getting comments for {post_url}: {e}")
                return None, []
        except Exception as e:
            print(f"Error getting comments: {e}")
            return None, []
    
    def post_warning_comment(self, post_url, username, comment_id):
        """
        Post a warning reply to a suspected bot comment
        
        Args:
            post_url (str): URL of the Instagram post
            username (str): Username being warned about
            comment_id (str): ID of the comment to reply to
            
        Returns:
            bool: Whether posting was successful
        """
        if not self.is_logged_in and not self.login():
            return False
        
        try:
            # Warning messages
            warning_messages = [
                f"⚠️ This account (@{username}) shows patterns of automated behavior. Be cautious with this information.",
                f"🤖 Activity analysis suggests @{username} may be automated. Verify claims independently.",
                f"📝 Automated account alert: @{username} displays bot-like behavior patterns."
            ]
            
            # Choose a random warning message
            warning = random.choice(warning_messages)
            
            # Post the reply
            try:
                media_pk = self.client.media_pk_from_url(post_url)
                self.client.media_comment(media_pk, warning, replied_to_comment_id=comment_id)
                print(f"Posted warning reply to @{username}'s comment")
                return True
            except Exception as e:
                print(f"Error posting comment: {e}")
                # Try without replied_to_comment_id as fallback
                try:
                    media_pk = self.client.media_pk_from_url(post_url)
                    warning = f"⚠️ Re: @{username} - {warning}"  # Add mention to make it clear who we're replying to
                    self.client.media_comment(media_pk, warning)
                    print(f"Posted warning (without direct reply feature) about @{username}")
                    return True
                except Exception as e2:
                    print(f"Fallback method also failed: {e2}")
                    return False
        except Exception as e:
            print(f"Error posting warning: {e}")
            return False
    
    def analyze_user_activity(self, username):
        """
        Advanced analysis of user activity with more sophisticated bot detection
        
        This is a higher-level method that combines user info and media analysis
        to determine behavioral patterns.
        
        Args:
            username (str): Instagram username to analyze
            
        Returns:
            dict: Analysis results including bot patterns
        """
        user_info = self.get_user_info(username)
        if not user_info:
            return None
            
        # If verified account, return early with low bot probability
        if user_info['is_verified']:
            return {
                'username': username,
                'bot_likelihood': 0.05,  # Very low probability for verified accounts
                'indicators': {'verified_account': True},
                'analysis': {
                    'is_verified': True,
                    'follower_count': user_info['follower_count'],
                    'following_count': user_info['following_count']
                }
            }
            
        # Get user media to analyze posting patterns
        user_medias = self.get_user_media(username, 20)
        
        # Continue with analysis for non-verified accounts
        if len(user_medias) >= 2:
            # Calculate time differences between posts
            time_differences = []
            engagement_ratios = []
            
            for i in range(len(user_medias)-1):
                # Time pattern analysis
                curr_time = user_medias[i]['timestamp']
                next_time = user_medias[i+1]['timestamp']
                time_diff = (curr_time - next_time).total_seconds() / 3600  # Convert to hours
                time_differences.append(time_diff)
                
                # Engagement analysis (likes + comments relative to followers)
                engagement = (user_medias[i]['like_count'] + user_medias[i]['comment_count']) / (user_info['follower_count'] or 1)
                engagement_ratios.append(engagement)
            
            # Calculate metrics
            avg_post_interval = sum(time_differences) / len(time_differences) if time_differences else 0
            avg_engagement = sum(engagement_ratios) / len(engagement_ratios) if engagement_ratios else 0
            
            # Calculate standard deviation if we have enough data points
            posting_regularity = statistics.stdev(time_differences) if len(time_differences) > 1 else 0
            
            # More sophisticated bot indicators
            bot_indicators = {
                'suspiciously_regular_posting': posting_regularity < 1,  # Very consistent posting times
                'extremely_low_engagement': avg_engagement < 0.005,  # Less than 0.5% engagement rate
                'high_following_ratio': user_info['following_count'] / (user_info['follower_count'] + 1) > 10,  # Following many more than followers
                'suspicious_username': bool(re.search(r'(bot|follow|auto|\d{4})$', username.lower())),  # Username contains suspicious patterns
                'excessive_post_volume': user_info['media_count'] > 1000 and user_info['follower_count'] < 1000  # Many posts, few followers
            }
            
            # Calculate bot likelihood with weighted factors
            weights = {
                'suspiciously_regular_posting': 0.3,
                'extremely_low_engagement': 0.3,
                'high_following_ratio': 0.2,
                'suspicious_username': 0.1,
                'excessive_post_volume': 0.1
            }
            
            weighted_score = sum(weights[indicator] for indicator, value in bot_indicators.items() if value)
            
            # Return complete analysis
            return {
                'username': username,
                'bot_likelihood': weighted_score,
                'indicators': bot_indicators,
                'analysis': {
                    'avg_hours_between_posts': avg_post_interval,
                    'posting_regularity': posting_regularity,
                    'avg_engagement_rate': avg_engagement * 100,  # Convert to percentage
                    'follower_count': user_info['follower_count'],
                    'following_count': user_info['following_count'],
                    'post_count': user_info['media_count'],
                    'has_profile_pic': user_info['has_profile_pic'],
                    'is_private': user_info['is_private']
                }
            }
        else:
            # Not enough posts to analyze patterns
            return {
                'username': username,
                'analysis': {
                    'follower_count': user_info['follower_count'],
                    'following_count': user_info['following_count'],
                    'post_count': user_info['media_count'],
                    'has_profile_pic': user_info['has_profile_pic'],
                    'is_private': user_info['is_private'],
                    'insufficient_data': True
                }
            }
    
    def analyze_post_commenters(self, post_url, max_comments=20):
        """
        Analyzes commenters on a post to detect potential bot accounts
        
        Args:
            post_url (str): URL of the Instagram post
            max_comments (int): Maximum number of comments to analyze
            
        Returns:
            dict: Analysis results including detected bots
        """
        post_id, comments = self.get_post_comments(post_url, max_comments)
        if not post_id:
            return None
        
        print(f"Found {len(comments)} comments to analyze")
        
        results = []
        detected_bots = []
        
        # Analyze each commenter
        for comment in comments:
            username = comment['username']
            print(f"\nAnalyzing commenter: {username}")
            
            # Skip our own comments
            if username == self.username:
                print("Skipping our own comment")
                continue
            
            # Analyze this commenter
            analysis = self.analyze_user_activity(username)
            
            if analysis:
                bot_likelihood = analysis.get('bot_likelihood', 0)
                print(f"Bot likelihood: {bot_likelihood*100:.1f}%")
                results.append(analysis)
                
                # Track likely bots
                if bot_likelihood > 0.5:
                    detected_bots.append({
                        'username': username,
                        'comment_text': comment['text'],
                        'comment_pk': comment['id'],
                        'bot_likelihood': bot_likelihood
                    })
        
        return {
            'post_pk': post_id,
            'post_url': post_url,
            'total_commenters': len(results),
            'likely_bots': detected_bots,
            'all_results': results
        }
    
    def get_user_posts(self, username, limit=3):
        """
        Get recent posts from a user
        
        Args:
            username (str): Instagram username
            limit (int): Maximum number of posts to retrieve
            
        Returns:
            list: List of post URLs
        """
        if not self.is_logged_in and not self.login():
            return []
        
        try:
            # Get user info
            user_info = self.client.user_info_by_username(username)
            
            # Try different methods to get recent posts
            try:
                # First try the regular method
                medias = self.client.user_medias(user_info.pk, limit)
            except KeyError as e:
                # If that fails, try the alternative method (v1 API)
                print(f"Notice: Using alternative method to fetch posts due to API change")
                try:
                    medias = self.client.user_medias_v1(user_info.pk, limit)
                except Exception as e2:
                    print(f"Alternative method failed: {e2}")
                    # Try another approach if available
                    try:
                        medias = self.client.user_feed(user_info.pk, limit)
                    except Exception as e3:
                        print(f"All methods failed: {e3}")
                        # Last resort - try to scrape from user profile
                        try:
                            username_info = self.client.username_info(username)
                            media_ids = username_info.get('media', {}).get('nodes', [])[:limit]
                            media_codes = [node.get('code') for node in media_ids if 'code' in node]
                            return [f"https://www.instagram.com/p/{code}/" for code in media_codes if code]
                        except Exception as e4:
                            print(f"Final attempt failed: {e4}")
                            return []
            
            # Format into URLs
            post_urls = [f"https://www.instagram.com/p/{media.code}/" for media in medias]
            
            return post_urls
        except Exception as e:
            print(f"Error getting posts for {username}: {e}")
            return []