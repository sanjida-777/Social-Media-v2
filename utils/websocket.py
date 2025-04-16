import logging
from datetime import datetime
from flask import session, request, g
from flask_socketio import emit, join_room, leave_room, disconnect

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
    logger.info(f"Client connected: {request.sid}")
    
    # Always allow connection, authentication will happen later
    emit('connected', {
        'status': 'connected', 
        'authenticated': False,
        'timestamp': datetime.now().isoformat()
    })
    
    return True

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")
    
    # Find user_id by socket id
    user_id = None
    for uid, sid in connected_clients.items():
        if sid == request.sid:
            user_id = uid
            break
    
    if user_id:
        logger.info(f"Authenticated client disconnected: {user_id}")
        del connected_clients[user_id]

        # Update user's online status
        try:
            from models import User
            from database import db
            
            user = User.query.get(user_id)
            if user:
                user.is_active = False
                user.last_online = datetime.now()
                db.session.commit()

                # Broadcast user's offline status
                emit('user_status', {
                    'user_id': user.id,
                    'username': user.username,
                    'status': 'offline'
                }, broadcast=True)
        except Exception as e:
            logger.error(f"Error updating user status on disconnect: {str(e)}")

@socketio.on('auth')
def handle_auth(data):
    """Handle client authentication"""
    logger.info(f"Auth request received from {request.sid}")
    
    # Get user ID from session
    user_id = session.get('user_id')
    if not user_id:
        logger.warning(f"Authentication failed: No user_id in session for {request.sid}")
        emit('auth_response', {'status': 'error', 'message': 'Authentication failed'})
        return

    try:
        # Get user from database
        from models import User
        from database import db
        
        user = User.query.get(user_id)
        if not user:
            logger.warning(f"Authentication failed: User {user_id} not found in database")
            emit('auth_response', {'status': 'error', 'message': 'User not found'})
            return

        # Store client connection
        connected_clients[user_id] = request.sid
        
        # Join user's personal room
        room_name = f"user_{user_id}"
        join_room(room_name)
        logger.info(f"Client {request.sid} joined room: {room_name}")

        # Update user's online status
        user.is_active = True
        user.last_online = datetime.now()
        db.session.commit()

        # Broadcast user's online status
        emit('user_status', {
            'user_id': user.id,
            'username': user.username,
            'status': 'online'
        }, broadcast=True)

        # Send success response
        logger.info(f"Client authenticated: {user_id} ({user.username})")
        emit('auth_response', {
            'status': 'success', 
            'user_id': user_id,
            'username': user.username
        })
    except Exception as e:
        logger.error(f"Error during authentication: {str(e)}")
        emit('auth_response', {'status': 'error', 'message': f'Server error: {str(e)}'})

@socketio.on('error')
def handle_error(error):
    """Handle WebSocket errors"""
    logger.error(f"WebSocket error: {error}")

@socketio.on('message')
def handle_message(data):
    """Handle generic messages"""
    logger.info(f"Message received from {request.sid}: {data}")
    
    # Find user_id by socket id
    user_id = None
    for uid, sid in connected_clients.items():
        if sid == request.sid:
            user_id = uid
            break
    
    if not user_id:
        logger.warning(f"Message from unauthenticated client: {request.sid}")
        return
    
    # Process message based on type
    if isinstance(data, dict) and 'type' in data:
        logger.info(f"Processing message of type: {data['type']}")
        # Add processing logic here if needed
    
    # Echo back for testing
    emit('message', {'echo': data, 'timestamp': datetime.now().isoformat()})

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
