import logging
from flask import jsonify, g
from models import User
from routes.api import api_bp

# Set up logger
logger = logging.getLogger(__name__)

@api_bp.route('/user/<int:user_id>', methods=['GET'])
def get_user_by_id(user_id):
    """Get user data by ID"""
    try:
        # Find user by ID
        user = User.query.get(user_id)
        
        if not user:
            logger.warning(f"User not found with ID: {user_id}")
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Format user data
        user_data = {
            'id': user.id,
            'uid': user.uid,
            'username': user.username,
            'email': user.email,
            'profile_pic': user.profile_pic,
            'bio': user.bio,
            'created_at': user.created_at.isoformat(),
            'last_online': user.last_online.isoformat() if user.last_online else None
        }
        
        # Return response
        return jsonify({
            'success': True,
            'user': user_data
        })
        
    except Exception as e:
        logger.error(f"Error getting user data: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while getting user data'
        }), 500
