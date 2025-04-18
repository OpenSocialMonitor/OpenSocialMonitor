"""
OpenSocialMonitor - An open-source toolkit for detecting and monitoring bot activity on social media platforms

This package provides tools for:
- Identifying automated accounts based on behavioral patterns
- Monitoring social media platforms for coordinated manipulation
- Warning users about potential bot accounts

For usage information, see: 
https://github.com/OpenSocialMonitor/OpenSocialMonitor
"""

# Package metadata
__version__ = '0.1.0'

# Import core components for easy access
from .platforms.instagram import InstagramPlatform
from .detection.indicators import calculate_bot_likelihood, detect_coordination
from .database.manager import DatabaseManager

# Import singleton database instance
from src.database import db

# Platform mapping
PLATFORMS = {
    'instagram': InstagramPlatform
}

# Configuration constants
DEFAULT_BOT_THRESHOLD = 0.6
DEFAULT_COORDINATION_THRESHOLD = 0.7

def get_platform(platform_name='instagram'):
    """
    Get an initialized platform connector
    
    Args:
        platform_name (str): Name of the platform ('instagram' is currently the only supported option)
        
    Returns:
        object: Platform connector instance
        
    Raises:
        ValueError: If platform is not supported
    """
    if platform_name.lower() not in PLATFORMS:
        raise ValueError(f"Unsupported platform: {platform_name}. Supported platforms: {', '.join(PLATFORMS.keys())}")
    
    return PLATFORMS[platform_name.lower()]()

def monitor_post(post_url, platform_name='instagram', threshold=DEFAULT_BOT_THRESHOLD, store_results=True):
    """
    Monitor a single post for bot activity
    
    This is a convenience function that handles platform initialization
    and bot detection in a single call.
    
    Args:
        post_url (str): URL of the post to monitor
        platform_name (str): Platform to use ('instagram' is currently the only supported option)
        threshold (float): Minimum likelihood score to consider an account a bot (0-1)
        store_results (bool): Whether to store results in the database
        
    Returns:
        dict: Results including detected bots and their likelihood scores
    """
    # Get the appropriate platform connector
    try:
        platform = get_platform(platform_name)
        if not platform.login():
            return {"error": "Failed to login to platform"}
    except ValueError as e:
        return {"error": str(e)}
    
    # Get comments from the post
    post_id, comments = platform.get_post_comments(post_url)
    if not post_id:
        return {"error": "Failed to retrieve comments"}
    
    # Analyze each commenter
    results = []
    detected_bots = []
    
    for comment in comments:
        username = comment['username']
        
        # Skip our own comments
        if username == platform.username:
            continue
        
        # Get user data if available
        user_data = platform.get_user_info(username)
        
        # Calculate bot likelihood
        bot_likelihood, indicators = calculate_bot_likelihood(
            username, 
            comment['text'],
            user_data
        )
        
        # Add to results
        results.append({
            'username': username,
            'comment_text': comment['text'],
            'bot_likelihood': bot_likelihood,
            'indicators': indicators
        })
        
        # Track likely bots
        if bot_likelihood >= threshold:
            detected_bots.append({
                'username': username,
                'comment_text': comment['text'],
                'comment_id': comment['id'],
                'bot_likelihood': bot_likelihood,
                'indicators': indicators
            })
            
            # Store in database if requested
            if store_results:
                # Add post to database if it doesn't exist
                db.add_processed_post(post_id, post_url, 'unknown_user', platform_name)
                
                # Add bot detection to database
                db.add_detected_bot(
                    username=username,
                    comment_id=comment['id'],
                    post_id=post_id,
                    bot_likelihood=bot_likelihood,
                    comment_text=comment['text']
                )
    
    # Check for coordination
    coordination = detect_coordination(comments)
    
    return {
        'post_id': post_id,
        'post_url': post_url,
        'total_comments': len(comments),
        'total_analyzed': len(results),
        'detected_bots': detected_bots,
        'coordination': coordination,
        'platform': platform_name
    }

def analyze_account(username, platform_name='instagram'):
    """
    Analyze a user account for bot-like behavior
    
    Args:
        username (str): Username to analyze
        platform_name (str): Platform to use ('instagram' is currently the only supported option)
        
    Returns:
        dict: Analysis results including bot likelihood
    """
    # Get platform connector
    try:
        platform = get_platform(platform_name)
        if not platform.login():
            return {"error": "Failed to login to platform"}
    except ValueError as e:
        return {"error": str(e)}
    
    # Get user data
    user_data = platform.get_user_info(username)
    if not user_data:
        return {"error": f"Failed to retrieve user information for {username}"}
    
    # Get detailed activity data if available
    activity_data = platform.analyze_user_activity(username)
    
    # Calculate bot likelihood
    if activity_data and 'bot_likelihood' in activity_data:
        # Use the platform's analysis if available
        bot_likelihood = activity_data['bot_likelihood']
        indicators = activity_data.get('indicators', {})
    else:
        # Fall back to basic detection
        bot_likelihood, indicators = calculate_bot_likelihood(username, user_data=user_data)
    
    return {
        'username': username,
        'platform': platform_name,
        'bot_likelihood': bot_likelihood,
        'indicators': indicators,
        'user_data': user_data,
        'activity_data': activity_data
    }

def list_pending_bots():
    """
    List all detected bots pending approval
    
    Returns:
        list: Detected bots pending review
    """
    return db.get_pending_bots()

def approve_bot_warning(bot_id, platform_name='instagram'):
    """
    Approve and send a warning for a detected bot
    
    Args:
        bot_id (int): ID of the detected bot
        platform_name (str): Platform to use
        
    Returns:
        bool: Whether the warning was sent successfully
    """
    # Get bot details
    bot_info = db.get_bot_details(bot_id)
    if not bot_info:
        return False
    
    # Get platform connector
    try:
        platform = get_platform(platform_name)
        if not platform.login():
            return False
    except ValueError:
        return False
    
    # Extract needed info
    username, _, _, post_url, _, _, comment_id, _ = bot_info
    
    # Post warning comment
    success = platform.post_warning_comment(post_url, username, comment_id)
    
    # Update database if successful
    if success:
        db.update_bot_warning_status(bot_id, True, True)
    
    return success