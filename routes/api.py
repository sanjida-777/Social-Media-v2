import logging
from flask import Blueprint, jsonify, request, g
from models import User, Post, Friend, Follower

# Set up logger
logger = logging.getLogger(__name__)

# Create blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/profile', methods=['GET'])
@api_bp.route('/profile/<username>', methods=['GET'])
def get_profile(username=None):
    """Get profile data for a user by username or user ID"""
    try:
        # Get page parameter for pagination
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        # Get user by UID or username
        uid = request.args.get('uid')

        if uid:
            # Get user by UID (10-digit identifier)
            user = User.query.filter_by(uid=uid).first()
        elif username:
            # Get user by username
            user = User.query.filter_by(username=username).first()
        else:
            return jsonify({
                'success': False,
                'error': 'No username or user UID provided'
            }), 400

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        # Get friendship status
        friendship_status = 'none'
        if g.user:
            # Check if they are friends
            friendship = Friend.query.filter(
                ((Friend.user_id == g.user.id) & (Friend.friend_id == user.id)) |
                ((Friend.user_id == user.id) & (Friend.friend_id == g.user.id))
            ).first()

            if friendship:
                if friendship.status == 'accepted':
                    friendship_status = 'accepted'
                elif friendship.status == 'pending':
                    if friendship.user_id == g.user.id:
                        friendship_status = 'pending'  # We sent the request
                    else:
                        friendship_status = 'received'  # We received the request

        # Check if following
        is_following = False
        if g.user:
            follow = Follower.query.filter_by(
                follower_id=g.user.id,
                user_id=user.id
            ).first()
            is_following = follow is not None

        # Get user's posts with pagination
        posts = Post.query.filter_by(user_id=user.id).order_by(Post.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        # Get friend count
        friend_count = Friend.query.filter(
            ((Friend.user_id == user.id) | (Friend.friend_id == user.id)) &
            (Friend.status == 'accepted')
        ).count()

        # Get follower count
        follower_count = Follower.query.filter_by(user_id=user.id).count()

        # Get following count
        following_count = Follower.query.filter_by(follower_id=user.id).count()

        # Format posts
        formatted_posts = []
        for post in posts.items:
            formatted_posts.append({
                'id': post.id,
                'user_id': post.user_id,
                'author': user.username,
                'profile_pic': user.profile_pic,
                'content': post.content,
                'created_at': post.created_at.isoformat(),
                'like_count': 0,  # Placeholder, would need to implement likes
                'comment_count': 0,  # Placeholder, would need to implement comments
                'liked_by_user': False,  # Placeholder
                'media': []  # Placeholder for post media
            })

        # Format user data
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'profile_pic': user.profile_pic,
            'cover_pic': user.cover_pic,
            'bio': user.bio,
            'created_at': user.created_at.isoformat(),
            'last_online': user.last_online.isoformat() if user.last_online else None
        }

        # Get friends list
        friends = []
        if friend_count > 0:
            # Get friendships where user is either user_id or friend_id
            friendships = Friend.query.filter(
                ((Friend.user_id == user.id) | (Friend.friend_id == user.id)) &
                (Friend.status == 'accepted')
            ).limit(6).all()

            for friendship in friendships:
                friend_id = friendship.friend_id if friendship.user_id == user.id else friendship.user_id
                friend = User.query.get(friend_id)
                if friend:
                    friends.append({
                        'id': friend.id,
                        'username': friend.username,
                        'profile_pic': friend.profile_pic
                    })

        # Return response
        return jsonify({
            'success': True,
            'user': user_data,
            'posts': formatted_posts,
            'friends': friends,
            'friendship_status': friendship_status,
            'is_following': is_following,
            'friend_count': friend_count,
            'follower_count': follower_count,
            'following_count': following_count,
            'pagination': {
                'current_page': posts.page,
                'total_pages': posts.pages,
                'total_items': posts.total,
                'per_page': posts.per_page
            }
        })

    except Exception as e:
        logger.error(f"Error getting profile data: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while getting profile data'
        }), 500

# Feed API endpoint
@api_bp.route('/feed', methods=['GET'])
def get_feed():
    """Get feed data for the current user"""
    try:
        if not g.user:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401

        # Get page parameter for pagination
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        # Get IDs of friends and people the user follows
        friend_ids = [f.friend_id for f in Friend.query.filter_by(user_id=g.user.id, status='accepted').all()]
        friend_ids += [f.user_id for f in Friend.query.filter_by(friend_id=g.user.id, status='accepted').all()]
        following_ids = [f.user_id for f in Follower.query.filter_by(follower_id=g.user.id).all()]

        # Combine IDs and add the user's own ID
        feed_user_ids = list(set(friend_ids + following_ids + [g.user.id]))

        # Get posts from these users
        posts_query = Post.query.filter(Post.user_id.in_(feed_user_ids))

        # Get total count for pagination
        total_posts = posts_query.count()

        # Get posts for the current page
        posts = posts_query.order_by(Post.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        # Format posts
        formatted_posts = []
        for post in posts.items:
            # Get post author
            author = User.query.get(post.user_id)

            formatted_posts.append({
                'id': post.id,
                'user_id': post.user_id,
                'author': author.username,
                'profile_pic': author.profile_pic,
                'content': post.content,
                'created_at': post.created_at.isoformat(),
                'like_count': 0,  # Placeholder, would need to implement likes
                'comment_count': 0,  # Placeholder, would need to implement comments
                'liked_by_user': False,  # Placeholder
                'media': []  # Placeholder for post media
            })

        # Return response
        return jsonify({
            'success': True,
            'posts': formatted_posts,
            'pagination': {
                'current_page': posts.page,
                'total_pages': posts.pages,
                'total_items': posts.total,
                'per_page': posts.per_page
            }
        })

    except Exception as e:
        logger.error(f"Error getting feed data: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while getting feed data'
        }), 500

# Stories API endpoint
@api_bp.route('/stories', methods=['GET'])
def get_stories():
    """Get stories for the current user"""
    try:
        if not g.user:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401

        # Import necessary models
        from models import Story, StoryView
        from datetime import datetime, timedelta

        # Get IDs of friends and people the user follows
        friend_ids = [f.friend_id for f in Friend.query.filter_by(user_id=g.user.id, status='accepted').all()]
        friend_ids += [f.user_id for f in Friend.query.filter_by(friend_id=g.user.id, status='accepted').all()]
        following_ids = [f.user_id for f in Follower.query.filter_by(follower_id=g.user.id).all()]

        # Combine IDs and add the user's own ID
        story_user_ids = list(set(friend_ids + following_ids + [g.user.id]))

        # Get active stories from these users (not expired)
        now = datetime.utcnow()
        active_stories = Story.query.filter(
            Story.user_id.in_(story_user_ids),
            Story.expires_at > now
        ).order_by(Story.created_at.desc()).all()

        # Group stories by user
        stories_by_user = {}
        for story in active_stories:
            if story.user_id not in stories_by_user:
                stories_by_user[story.user_id] = {
                    'user': User.query.get(story.user_id).serialize(),
                    'stories': []
                }

            # Check if user has viewed this story
            viewed = StoryView.query.filter_by(story_id=story.id, user_id=g.user.id).first() is not None

            story_data = {
                'id': story.id,
                'user_id': story.user_id,
                'story_type': story.story_type,
                'content': story.content,
                'media_url': story.media_url,
                'created_at': story.created_at.isoformat(),
                'expires_at': story.expires_at.isoformat(),
                'viewed': viewed
            }

            stories_by_user[story.user_id]['stories'].append(story_data)

        # Convert to list for JSON response
        result = list(stories_by_user.values())

        # Sort by whether user has viewed all stories
        result.sort(key=lambda x: all(s['viewed'] for s in x['stories']))

        return jsonify({
            'success': True,
            'story_users': result
        })

    except Exception as e:
        logger.error(f"Error getting stories: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while getting stories'
        }), 500
