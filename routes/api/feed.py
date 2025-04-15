import logging
from flask import jsonify, request, g
from models import User, Post, Friend, Follower
from routes.api import api_bp

# Set up logger
logger = logging.getLogger(__name__)

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
