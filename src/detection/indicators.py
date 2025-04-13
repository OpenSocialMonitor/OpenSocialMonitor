"""
Bot detection algorithms and indicators

This module provides functions for analyzing social media accounts
and determining the likelihood they are automated bots.
"""

import re
import statistics

def calculate_bot_likelihood(username, comment_text=None, user_data=None):
    """
    Calculate the likelihood that an account is a bot based on multiple signals
    
    Args:
        username (str): The account username
        comment_text (str, optional): Text of a comment for analysis
        user_data (dict, optional): User profile and activity data
        
    Returns:
        tuple: (likelihood_score, indicators_dict)
            - likelihood_score: Float between 0-1 (higher = more likely to be a bot)
            - indicators_dict: Dictionary of detection signals that contributed to the score
    """
    # Initialize scores for different types of signals
    text_pattern_score = 0
    behavioral_score = 0
    profile_score = 0
    
    # Initialize indicators dictionary to track what signals were detected
    bot_indicators = {}
    
    # Text pattern analysis (if comment text is provided)
    if comment_text:
        # Check for common bot phrases/patterns
        bot_phrases = [
            "check my profile", "check my bio", "click here", "make money fast",
            "follow me", "dm me", "link in bio", "check link", "join now", "earn money", 
            "work from home", "passive income", "click my profile"
        ]
        
        # Count matching phrases
        phrase_matches = [phrase for phrase in bot_phrases if phrase in comment_text.lower()]
        if phrase_matches:
            bot_indicators['suspicious_phrases'] = phrase_matches
            text_pattern_score += min(len(phrase_matches) * 0.1, 0.5)  # Cap at 0.5
        
        # Check for excessive emojis (often used by bots)
        emoji_count = len(re.findall(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF]', comment_text))
        if emoji_count > 5:
            bot_indicators['excessive_emojis'] = emoji_count
            text_pattern_score += min((emoji_count - 5) * 0.05, 0.2)
        
        # Check for URLs
        urls = re.findall(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', comment_text)
        if urls:
            bot_indicators['contains_urls'] = True
            text_pattern_score += 0.3
    
    # Behavioral analysis (if user data is provided)
    if user_data:
        # Skip analysis if verified account
        if user_data.get('is_verified', False):
            return 0.05, {'verified_account': True}
        
        # Check for suspiciously regular posting
        posting_regularity = user_data.get('posting_regularity', None)
        if posting_regularity is not None and posting_regularity < 1:
            bot_indicators['suspiciously_regular_posting'] = True
            behavioral_score += 0.3
        
        # Check for extremely low engagement
        engagement_rate = user_data.get('avg_engagement_rate', None)
        if engagement_rate is not None and engagement_rate < 0.5:  # Less than 0.5% engagement
            bot_indicators['extremely_low_engagement'] = True
            behavioral_score += 0.3
    
        # Profile analysis
        followers = user_data.get('follower_count', 0)
        following = user_data.get('following_count', 0)
        
        # High following to follower ratio
        if followers > 0 and following / followers > 10:
            bot_indicators['high_following_ratio'] = True
            profile_score += 0.2
        
        # Many posts but few followers
        post_count = user_data.get('post_count', 0)
        if post_count > 1000 and followers < 1000:
            bot_indicators['excessive_post_volume'] = True
            profile_score += 0.1
        
        # No profile picture
        if not user_data.get('has_profile_pic', True):
            bot_indicators['no_profile_pic'] = True
            profile_score += 0.2
    
    # Username pattern analysis
    if re.search(r'(bot|follow|auto|\d{4})$', username.lower()):
        bot_indicators['suspicious_username'] = True
        profile_score += 0.1
    
    # Calculate final score based on available signals
    if user_data and comment_text:
        # We have both user data and comment text
        final_score = (text_pattern_score * 0.4) + (behavioral_score * 0.4) + (profile_score * 0.2)
    elif user_data:
        # Only user data, no comment text
        final_score = (behavioral_score * 0.6) + (profile_score * 0.4)
    elif comment_text:
        # Only comment text, no user data
        final_score = text_pattern_score
    else:
        # Just username
        final_score = profile_score
    
    return min(final_score, 0.99), bot_indicators  # Cap at 0.99 to avoid absolute certainty

def detect_coordination(comments, timeframe_hours=24):
    """
    Detect coordinated behavior between accounts
    
    Args:
        comments (list): List of comments with user and text information
        timeframe_hours (int): Time window to consider for coordination
        
    Returns:
        list: Detected coordination networks
    """
    # Group comments by text to find identical comments
    comment_groups = {}
    
    for comment in comments:
        text = comment['text'].lower().strip()
        username = comment['username']
        timestamp = comment.get('created_at', None)
        
        if text not in comment_groups:
            comment_groups[text] = []
        
        comment_groups[text].append({
            'username': username,
            'timestamp': timestamp,
            'original_comment': comment
        })
    
    # Find coordination networks
    networks = []
    
    for text, comments in comment_groups.items():
        # Skip very short or common texts
        if len(text) < 10 or len(comments) < 2:
            continue
        
        # If the same text was used by multiple users
        if len(set(c['username'] for c in comments)) > 1:
            networks.append({
                'text': text,
                'users': list(set(c['username'] for c in comments)),
                'comment_count': len(comments),
                'confidence': min(0.5 + (len(comments) * 0.1), 0.9)  # Higher confidence with more comments
            })
    
    return networks