import logging
from flask import jsonify, request, g
from models import User, Post
from routes.api import api_bp

# Set up logger
logger = logging.getLogger(__name__)

@api_bp.route('/search', methods=['GET'])
def api_search():
    """Search for users and posts"""
    try:
        query = request.args.get('q', '').strip()

        if not query:
            return jsonify({'users': [], 'posts': []})

        # Search for users
        users = User.query.filter(
            User.username.ilike(f'%{query}%') |
            User.bio.ilike(f'%{query}%')
        ).limit(20).all()

        # Search for posts
        posts = Post.query.filter(
            Post.content.ilike(f'%{query}%')
        ).order_by(Post.created_at.desc()).limit(20).all()

        return jsonify({
            'success': True,
            'users': [user.serialize() for user in users],
            'posts': [post.serialize() for post in posts]
        })

    except Exception as e:
        logger.error(f"Error searching: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while searching'
        }), 500
