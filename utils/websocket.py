import logging
from datetime import datetime
from flask import session, request
from flask_socketio import emit, join_room, leave_room

# Import shared socketio instance
from socket_instance import socketio

# Set up logger
logger = logging.getLogger(__name__)

# Connected clients
connected_clients = {}

def init_socketio(app):
    """Initialize SocketIO handlers"""
    logger.info("WebSocket handlers initialized")
    return True

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    client_id = session.get('user_id')
    if not client_id:
        logger.warning("Unauthenticated connection attempt")
        return False

    logger.info(f"Client connected: {client_id}")
    connected_clients[client_id] = request.sid

    # Join user's personal room
    join_room(f"user_{client_id}")

    # Acknowledge connection
    emit('connected', {'status': 'connected', 'timestamp': datetime.now().isoformat()})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    client_id = session.get('user_id')
    if client_id and client_id in connected_clients:
        logger.info(f"Client disconnected: {client_id}")
        del connected_clients[client_id]

        # Leave user's personal room
        leave_room(f"user_{client_id}")

@socketio.on('auth')
def handle_auth(data):
    """Handle client authentication"""
    client_id = session.get('user_id')
    if not client_id:
        logger.warning("Authentication failed: No user_id in session")
        emit('auth_response', {'status': 'error', 'message': 'Authentication failed'})
        return

    logger.info(f"Client authenticated: {client_id}")
    emit('auth_response', {'status': 'success', 'user_id': client_id})

@socketio.on('error')
def handle_error(error):
    """Handle WebSocket errors"""
    logger.error(f"WebSocket error: {error}")

def send_to_user(user_id, event_type, data):
    """Send event to a specific user"""
    try:
        room = f"user_{user_id}"
        socketio.emit(event_type, data, room=room)
        logger.debug(f"Sent {event_type} to user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error sending {event_type} to user {user_id}: {str(e)}")
        return False

def broadcast_to_friends(user_id, event_type, data, friends_list=None):
    """Broadcast event to user's friends"""
    try:
        if not friends_list:
            # Import here to avoid circular imports
            from models import Friend

            # Get user's friends
            friends = Friend.query.filter_by(status='accepted').filter(
                (Friend.user_id == user_id) | (Friend.friend_id == user_id)
            ).all()

            friends_list = []
            for friend in friends:
                if friend.user_id == user_id:
                    friends_list.append(friend.friend_id)
                else:
                    friends_list.append(friend.user_id)

        # Send to each friend
        for friend_id in friends_list:
            send_to_user(friend_id, event_type, data)

        # Also send to the user themselves
        send_to_user(user_id, event_type, data)

        logger.debug(f"Broadcast {event_type} to {len(friends_list)} friends of user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error broadcasting {event_type} to friends of user {user_id}: {str(e)}")
        return False

def notify_new_post(post_id, user_id, author_name):
    """Notify friends about a new post"""
    data = {
        'type': 'new_post',
        'post_id': post_id,
        'user_id': user_id,
        'author': author_name,
        'timestamp': datetime.now().isoformat()
    }
    return broadcast_to_friends(user_id, 'message', data)

def notify_new_comment(comment_id, post_id, user_id, author_name, post_author_id):
    """Notify about a new comment"""
    data = {
        'type': 'new_comment',
        'comment_id': comment_id,
        'post_id': post_id,
        'user_id': user_id,
        'author': author_name,
        'timestamp': datetime.now().isoformat()
    }

    # Send to post author
    send_to_user(post_author_id, 'message', data)

    # Also send to the commenter if different from post author
    if user_id != post_author_id:
        send_to_user(user_id, 'message', data)

    return True

def notify_new_like(post_id, user_id, post_author_id, like_count):
    """Notify about a new like"""
    data = {
        'type': 'new_like',
        'post_id': post_id,
        'user_id': user_id,
        'like_count': like_count,
        'timestamp': datetime.now().isoformat()
    }

    # Send to post author
    send_to_user(post_author_id, 'message', data)

    return True
