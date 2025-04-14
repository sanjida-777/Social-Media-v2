import logging
from datetime import datetime, timedelta
from sqlalchemy import func

from models import UserInteraction, ChatMessage, PostLike, Comment, Friend

# Set up logger
logger = logging.getLogger(__name__)

def calculate_relationship_score(user_id, friend_id):
    """
    Calculate a relationship strength score between two users
    
    Factors considered:
    1. Message frequency (30%)
    2. Interactions (likes, comments) (30%)
    3. Profile visits (20%)
    4. Mutual friends (20%)
    
    Returns a normalized score between 0 and 1
    """
    # Factor 1: Message frequency
    message_score = calculate_message_score(user_id, friend_id)
    
    # Factor 2: Interactions (likes, comments)
    interaction_score = calculate_interaction_score(user_id, friend_id)
    
    # Factor 3: Profile visits
    profile_visit_score = calculate_profile_visit_score(user_id, friend_id)
    
    # Factor 4: Mutual friends
    mutual_friends_score = calculate_mutual_friends_score(user_id, friend_id)
    
    # Calculate final score with weights
    final_score = (
        (message_score * 0.3) + 
        (interaction_score * 0.3) + 
        (profile_visit_score * 0.2) + 
        (mutual_friends_score * 0.2)
    )
    
    logger.debug(f"Relationship score between {user_id} and {friend_id}: {final_score}")
    logger.debug(f"Scores: message={message_score}, interaction={interaction_score}, profile_visit={profile_visit_score}, mutual_friends={mutual_friends_score}")
    
    return final_score

def calculate_message_score(user_id, friend_id):
    """
    Calculate score based on message frequency
    """
    from app import db
    
    # Get message count in the last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    # Find chat groups that both users are in
    from models import ChatMember, ChatMessage
    
    # Get chat_ids where both users are members
    user_chats = db.session.query(ChatMember.chat_id).filter_by(user_id=user_id).subquery()
    friend_chats = db.session.query(ChatMember.chat_id).filter_by(user_id=friend_id).subquery()
    
    common_chats = db.session.query(user_chats.c.chat_id).filter(
        user_chats.c.chat_id.in_(db.session.query(friend_chats.c.chat_id))
    ).all()
    
    common_chat_ids = [chat[0] for chat in common_chats]
    
    if not common_chat_ids:
        return 0.0
    
    # Count messages between the two users in their common chats
    message_count = ChatMessage.query.filter(
        ChatMessage.chat_id.in_(common_chat_ids),
        ChatMessage.created_at >= thirty_days_ago,
        ((ChatMessage.user_id == user_id) | (ChatMessage.user_id == friend_id))
    ).count()
    
    # Calculate score (normalize up to 100 messages for max score)
    max_messages = 100
    message_score = min(message_count / max_messages, 1.0)
    
    return message_score

def calculate_interaction_score(user_id, friend_id):
    """
    Calculate score based on interactions (likes, comments)
    """
    # Get interaction counts in the last 60 days
    sixty_days_ago = datetime.utcnow() - timedelta(days=60)
    
    # Count likes from user to friend's posts
    from models import Post, PostLike, Comment
    
    # Get friend's posts
    friend_posts = Post.query.filter_by(user_id=friend_id).subquery()
    
    # Count likes
    user_likes_count = PostLike.query.filter(
        PostLike.post_id.in_(db.session.query(friend_posts.c.id)),
        PostLike.user_id == user_id,
        PostLike.created_at >= sixty_days_ago
    ).count()
    
    # Count comments
    user_comments_count = Comment.query.filter(
        Comment.post_id.in_(db.session.query(friend_posts.c.id)),
        Comment.user_id == user_id,
        Comment.created_at >= sixty_days_ago
    ).count()
    
    # Get user's posts
    user_posts = Post.query.filter_by(user_id=user_id).subquery()
    
    # Count likes from friend to user's posts
    friend_likes_count = PostLike.query.filter(
        PostLike.post_id.in_(db.session.query(user_posts.c.id)),
        PostLike.user_id == friend_id,
        PostLike.created_at >= sixty_days_ago
    ).count()
    
    # Count comments from friend to user's posts
    friend_comments_count = Comment.query.filter(
        Comment.post_id.in_(db.session.query(user_posts.c.id)),
        Comment.user_id == friend_id,
        Comment.created_at >= sixty_days_ago
    ).count()
    
    # Calculate total interaction count (comments worth 2x likes)
    total_interactions = user_likes_count + (user_comments_count * 2) + friend_likes_count + (friend_comments_count * 2)
    
    # Calculate score (normalize up to 50 interactions for max score)
    max_interactions = 50
    interaction_score = min(total_interactions / max_interactions, 1.0)
    
    return interaction_score

def calculate_profile_visit_score(user_id, friend_id):
    """
    Calculate score based on profile visits
    """
    # Count profile visits in both directions
    user_visits = UserInteraction.query.filter_by(
        user_id=user_id,
        target_id=friend_id,
        interaction_type='profile_visit'
    ).first()
    
    friend_visits = UserInteraction.query.filter_by(
        user_id=friend_id,
        target_id=user_id,
        interaction_type='profile_visit'
    ).first()
    
    user_visit_count = user_visits.interaction_count if user_visits else 0
    friend_visit_count = friend_visits.interaction_count if friend_visits else 0
    
    total_visits = user_visit_count + friend_visit_count
    
    # Calculate score (normalize up to 20 visits for max score)
    max_visits = 20
    visit_score = min(total_visits / max_visits, 1.0)
    
    return visit_score

def calculate_mutual_friends_score(user_id, friend_id):
    """
    Calculate score based on mutual friends
    """
    from app import db
    
    # Get user's friends
    user_friends_query = Friend.query.filter(
        ((Friend.user_id == user_id) | (Friend.friend_id == user_id)),
        Friend.status == 'accepted'
    )
    
    user_friend_ids = []
    for friendship in user_friends_query.all():
        if friendship.user_id == user_id:
            user_friend_ids.append(friendship.friend_id)
        else:
            user_friend_ids.append(friendship.user_id)
    
    # Get friend's friends
    friend_friends_query = Friend.query.filter(
        ((Friend.user_id == friend_id) | (Friend.friend_id == friend_id)),
        Friend.status == 'accepted'
    )
    
    friend_friend_ids = []
    for friendship in friend_friends_query.all():
        if friendship.user_id == friend_id:
            friend_friend_ids.append(friendship.friend_id)
        else:
            friend_friend_ids.append(friendship.user_id)
    
    # Find mutual friends
    mutual_friends = set(user_friend_ids).intersection(set(friend_friend_ids))
    mutual_friend_count = len(mutual_friends)
    
    # Calculate score (normalize up to 30 mutual friends for max score)
    max_mutual_friends = 30
    mutual_friends_score = min(mutual_friend_count / max_mutual_friends, 1.0)
    
    return mutual_friends_score
