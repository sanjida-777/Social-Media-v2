import logging
import math
from datetime import datetime, timedelta
from collections import defaultdict

from models import PostLike, Comment, UserInteraction, Friend

# Set up logger
logger = logging.getLogger(__name__)

def rank_posts(posts, user_id):
    """
    Rank posts based on a personalized algorithm for the given user
    
    Factors considered:
    1. Recency of post
    2. Relationship strength with post author
    3. Post engagement (likes, comments)
    4. User's previous engagement with similar posts
    
    Returns a sorted list of posts
    """
    if not posts:
        return []
    
    # Current time for recency calculations
    now = datetime.utcnow()
    
    # Calculate scores for each post
    post_scores = []
    for post in posts:
        score = calculate_post_score(post, user_id, now)
        post_scores.append((post, score))
    
    # Sort posts by score (highest first)
    post_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Extract just the posts from the sorted list
    ranked_posts = [post for post, score in post_scores]
    
    return ranked_posts

def calculate_post_score(post, user_id, now):
    """
    Calculate a score for a single post
    """
    # Factor 1: Recency score (newer posts score higher)
    max_recency_days = 3  # Posts older than this get minimal recency score
    post_age = now - post.created_at
    recency_score = max(0, 1 - (post_age.total_seconds() / (max_recency_days * 24 * 60 * 60)))
    
    # Factor 2: Relationship strength with post author
    relationship_score = get_relationship_strength(user_id, post.user_id)
    
    # Factor 3: Post engagement
    like_count = post.likes.count()
    comment_count = post.comments.count()
    
    # Normalize engagement (using a logarithmic scale to prevent very popular posts from dominating)
    engagement_score = 0
    if like_count > 0 or comment_count > 0:
        engagement_score = math.log1p(like_count + (comment_count * 2)) / 10  # Comments weighted more than likes
    
    # Factor 4: User's previous engagement with this author's posts
    author_engagement_score = get_author_engagement_score(user_id, post.user_id)
    
    # Calculate final score with weights
    # Weights: recency (40%), relationship (30%), engagement (20%), author engagement (10%)
    final_score = (
        (recency_score * 0.4) + 
        (relationship_score * 0.3) + 
        (engagement_score * 0.2) + 
        (author_engagement_score * 0.1)
    )
    
    logger.debug(f"Post {post.id} score: {final_score} (recency: {recency_score}, relationship: {relationship_score}, engagement: {engagement_score}, author_engagement: {author_engagement_score})")
    
    return final_score

def get_relationship_strength(user_id, author_id):
    """
    Calculate relationship strength between user and post author
    """
    # If it's the user's own post, highest relationship score
    if user_id == author_id:
        return 1.0
    
    # Check if they are friends
    friendship = Friend.query.filter(
        ((Friend.user_id == user_id) & (Friend.friend_id == author_id)) |
        ((Friend.user_id == author_id) & (Friend.friend_id == user_id))
    ).first()
    
    if friendship and friendship.status == 'accepted':
        # Return normalized relationship score (0.5-1.0 for friends)
        return 0.5 + (friendship.relationship_score / 2.0)
    
    # Non-friends get a lower base score
    return 0.2

def get_author_engagement_score(user_id, author_id):
    """
    Calculate a score based on user's engagement with the author's content
    """
    # If it's the user's own post, highest engagement score
    if user_id == author_id:
        return 1.0
    
    # Get interactions with this author
    interactions = UserInteraction.query.filter_by(
        user_id=user_id,
        target_id=author_id
    ).all()
    
    if not interactions:
        return 0.0
    
    # Calculate score based on interaction types and counts
    score = 0
    for interaction in interactions:
        if interaction.interaction_type == 'like':
            score += (0.05 * min(interaction.interaction_count, 10))
        elif interaction.interaction_type == 'comment':
            score += (0.1 * min(interaction.interaction_count, 5))
        elif interaction.interaction_type == 'profile_visit':
            score += (0.15 * min(interaction.interaction_count, 3))
        elif interaction.interaction_type == 'message':
            score += (0.2 * min(interaction.interaction_count, 5))
    
    # Normalize score to 0-1 range
    return min(score, 1.0)
