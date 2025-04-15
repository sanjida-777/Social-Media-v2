import logging
from datetime import datetime
from flask import jsonify, request, g
from models import User, Friend
from database import db
from routes.api import api_bp

# Set up logger
logger = logging.getLogger(__name__)

@api_bp.route('/friend_request/<username>', methods=['POST'])
def send_friend_request(username):
    """Send a friend request to a user"""
    try:
        # Check if user is logged in
        if not g.user:
            return jsonify({
                'success': False,
                'error': 'You must be logged in to send friend requests'
            }), 401
        
        # Find user by username
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Check if trying to send request to self
        if user.id == g.user.id:
            return jsonify({
                'success': False,
                'error': 'You cannot send a friend request to yourself'
            }), 400
        
        # Check if already friends
        existing_friendship = Friend.query.filter(
            ((Friend.user_id == g.user.id) & (Friend.friend_id == user.id) & (Friend.status == 'accepted')) |
            ((Friend.user_id == user.id) & (Friend.friend_id == g.user.id) & (Friend.status == 'accepted'))
        ).first()
        
        if existing_friendship:
            return jsonify({
                'success': False,
                'error': 'You are already friends with this user'
            }), 400
        
        # Check if request already sent
        existing_request = Friend.query.filter_by(
            user_id=g.user.id, friend_id=user.id, status='pending'
        ).first()
        
        if existing_request:
            return jsonify({
                'success': False,
                'error': 'Friend request already sent'
            }), 400
        
        # Check if request already received
        existing_request = Friend.query.filter_by(
            user_id=user.id, friend_id=g.user.id, status='pending'
        ).first()
        
        if existing_request:
            # Auto-accept the request
            existing_request.status = 'accepted'
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Friend request accepted'
            })
        
        # Create friend request
        friend_request = Friend(
            user_id=g.user.id,
            friend_id=user.id,
            status='pending',
            created_at=datetime.now()
        )
        
        db.session.add(friend_request)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Friend request sent'
        })
        
    except Exception as e:
        logger.error(f"Error sending friend request: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while sending friend request'
        }), 500

@api_bp.route('/friend_request/<username>/accept', methods=['POST'])
def accept_friend_request(username):
    """Accept a friend request from a user"""
    try:
        # Check if user is logged in
        if not g.user:
            return jsonify({
                'success': False,
                'error': 'You must be logged in to accept friend requests'
            }), 401
        
        # Find user by username
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Find friend request
        friend_request = Friend.query.filter_by(
            user_id=user.id, friend_id=g.user.id, status='pending'
        ).first()
        
        if not friend_request:
            return jsonify({
                'success': False,
                'error': 'No pending friend request found from this user'
            }), 404
        
        # Accept friend request
        friend_request.status = 'accepted'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Friend request accepted'
        })
        
    except Exception as e:
        logger.error(f"Error accepting friend request: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while accepting friend request'
        }), 500

@api_bp.route('/friend_request/<username>/decline', methods=['POST'])
def decline_friend_request(username):
    """Decline a friend request from a user"""
    try:
        # Check if user is logged in
        if not g.user:
            return jsonify({
                'success': False,
                'error': 'You must be logged in to decline friend requests'
            }), 401
        
        # Find user by username
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Find friend request
        friend_request = Friend.query.filter_by(
            user_id=user.id, friend_id=g.user.id, status='pending'
        ).first()
        
        if not friend_request:
            return jsonify({
                'success': False,
                'error': 'No pending friend request found from this user'
            }), 404
        
        # Delete friend request
        db.session.delete(friend_request)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Friend request declined'
        })
        
    except Exception as e:
        logger.error(f"Error declining friend request: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while declining friend request'
        }), 500

@api_bp.route('/friend/<username>/remove', methods=['POST'])
def remove_friend(username):
    """Remove a friend"""
    try:
        # Check if user is logged in
        if not g.user:
            return jsonify({
                'success': False,
                'error': 'You must be logged in to remove friends'
            }), 401
        
        # Find user by username
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Find friendship records
        friendship1 = Friend.query.filter_by(
            user_id=g.user.id, friend_id=user.id, status='accepted'
        ).first()
        
        friendship2 = Friend.query.filter_by(
            user_id=user.id, friend_id=g.user.id, status='accepted'
        ).first()
        
        if not friendship1 and not friendship2:
            return jsonify({
                'success': False,
                'error': 'You are not friends with this user'
            }), 404
        
        # Delete friendship records
        if friendship1:
            db.session.delete(friendship1)
        
        if friendship2:
            db.session.delete(friendship2)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Friend removed'
        })
        
    except Exception as e:
        logger.error(f"Error removing friend: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while removing friend'
        }), 500
