import logging
from flask import request, g
from flask_socketio import emit, join_room, leave_room
# Get shared socketio instance
from socket_instance import socketio
from models import User, Message, Conversation
from database import db
from datetime import datetime, timezone

# Set up logger
logger = logging.getLogger(__name__)

# Note: The connect and disconnect handlers are now in utils/websocket.py
# to avoid duplicate handlers

@socketio.on('join_conversation')
def handle_join_conversation(data):
    """Join a conversation room"""
    logger.info(f"Join conversation request from {request.sid}: {data}")
    
    # Find user_id by socket id
    user_id = None
    for uid, sid in socketio.server.environ.get('socketio', {}).get('rooms', {}).items():
        if sid == request.sid:
            user_id = uid
            break
    
    if not user_id:
        logger.warning(f"Join conversation from unauthenticated client: {request.sid}")
        return {'success': False, 'error': 'Not authenticated'}
    
    # Get user from database
    from models import User
    user = User.query.get(user_id)
    if not user:
        logger.warning(f"User {user_id} not found in database")
        return {'success': False, 'error': 'User not found'}

    conversation_id = data.get('conversation_id')
    if not conversation_id:
        return {'success': False, 'error': 'Missing conversation ID'}

    # Check if user is part of this conversation
    conversation = Conversation.query.get(conversation_id)
    if not conversation:
        return {'success': False, 'error': 'Conversation not found'}

    if conversation.user1_id != user.id and conversation.user2_id != user.id:
        logger.warning(f"User {user.username} attempted to join conversation {conversation_id} they're not part of")
        return {'success': False, 'error': 'Not authorized to join this conversation'}

    # Join the room
    room_name = f"conversation_{conversation_id}"
    join_room(room_name)
    logger.info(f"User {user.username} joined room: {room_name}")

    # Mark messages as read
    unread_messages = Message.query.filter_by(
        conversation_id=conversation_id,
        recipient_id=user.id,
        read=False
    ).all()

    for message in unread_messages:
        message.read = True

    db.session.commit()

    # Notify the other user that messages have been read
    other_user_id = conversation.user2_id if conversation.user1_id == user.id else conversation.user1_id
    emit('messages_read', {
        'conversation_id': conversation_id,
        'user_id': user.id
    }, room=f"user_{other_user_id}")
    
    return {'success': True}

@socketio.on('leave_conversation')
def handle_leave_conversation(data):
    """Leave a conversation room"""
    logger.info(f"Leave conversation request from {request.sid}: {data}")
    
    # Find user_id by socket id
    user_id = None
    for uid, sid in socketio.server.environ.get('socketio', {}).get('rooms', {}).items():
        if sid == request.sid:
            user_id = uid
            break
    
    if not user_id:
        logger.warning(f"Leave conversation from unauthenticated client: {request.sid}")
        return {'success': False, 'error': 'Not authenticated'}
    
    # Get user from database
    from models import User
    user = User.query.get(user_id)
    if not user:
        logger.warning(f"User {user_id} not found in database")
        return {'success': False, 'error': 'User not found'}

    conversation_id = data.get('conversation_id')
    if not conversation_id:
        return {'success': False, 'error': 'Missing conversation ID'}

    # Leave the room
    room_name = f"conversation_{conversation_id}"
    leave_room(room_name)
    logger.info(f"User {user.username} left room: {room_name}")
    
    return {'success': True}

@socketio.on('send_message')
def handle_send_message(data):
    """Handle new message"""
    logger.info(f"Send message request from {request.sid}: {data}")
    
    # Find user_id by socket id
    user_id = None
    for uid, sid in socketio.server.environ.get('socketio', {}).get('rooms', {}).items():
        if sid == request.sid:
            user_id = uid
            break
    
    if not user_id:
        logger.warning(f"Send message from unauthenticated client: {request.sid}")
        return {'success': False, 'error': 'Not authenticated'}
    
    # Get user from database
    from models import User
    user = User.query.get(user_id)
    if not user:
        logger.warning(f"User {user_id} not found in database")
        return {'success': False, 'error': 'User not found'}

    recipient_id = data.get('recipient_id')
    content = data.get('content')

    if not recipient_id or not content:
        return {'success': False, 'error': 'Missing required fields'}

    # Get recipient
    recipient = User.query.get(recipient_id)
    if not recipient:
        return {'success': False, 'error': 'Recipient not found'}

    # Find or create conversation
    conversation = Conversation.query.filter(
        ((Conversation.user1_id == user.id) & (Conversation.user2_id == recipient.id)) |
        ((Conversation.user1_id == recipient.id) & (Conversation.user2_id == user.id))
    ).first()

    if not conversation:
        conversation = Conversation(
            user1_id=user.id,
            user2_id=recipient.id
        )
        db.session.add(conversation)
        db.session.commit()

    # Create message
    message = Message(
        conversation_id=conversation.id,
        sender_id=user.id,
        recipient_id=recipient.id,
        content=content,
        created_at=datetime.now(timezone.utc)
    )
    db.session.add(message)

    # Update conversation last_message_at
    conversation.last_message_at = message.created_at
    db.session.commit()

    # Prepare message data for sending
    message_data = {
        'id': message.id,
        'conversation_id': message.conversation_id,
        'sender_id': message.sender_id,
        'sender_username': user.username,
        'sender_profile_pic': user.profile_pic,
        'recipient_id': message.recipient_id,
        'content': message.content,
        'created_at': message.created_at.isoformat(),
        'read': message.read
    }

    # Emit to conversation room
    room_name = f"conversation_{conversation.id}"
    emit('new_message', message_data, room=room_name)

    # Also emit to recipient's user room (in case they're not in the conversation room)
    emit('new_message', message_data, room=f"user_{recipient.id}")

    # Return success to sender
    return {'success': True, 'message': message_data}

@socketio.on('typing')
def handle_typing(data):
    """Handle typing indicator"""
    logger.info(f"Typing indicator from {request.sid}: {data}")
    
    # Find user_id by socket id
    user_id = None
    for uid, sid in socketio.server.environ.get('socketio', {}).get('rooms', {}).items():
        if sid == request.sid:
            user_id = uid
            break
    
    if not user_id:
        logger.warning(f"Typing indicator from unauthenticated client: {request.sid}")
        return {'success': False, 'error': 'Not authenticated'}
    
    # Get user from database
    from models import User
    user = User.query.get(user_id)
    if not user:
        logger.warning(f"User {user_id} not found in database")
        return {'success': False, 'error': 'User not found'}

    conversation_id = data.get('conversation_id')
    if not conversation_id:
        return {'success': False, 'error': 'Missing conversation ID'}

    # Check if user is part of this conversation
    conversation = Conversation.query.get(conversation_id)
    if not conversation:
        return {'success': False, 'error': 'Conversation not found'}

    if conversation.user1_id != user.id and conversation.user2_id != user.id:
        return {'success': False, 'error': 'Not authorized for this conversation'}

    # Emit typing event to conversation room
    room_name = f"conversation_{conversation_id}"
    emit('typing', {
        'user_id': user.id,
        'username': user.username,
        'conversation_id': conversation_id
    }, room=room_name, include_self=False)
    
    return {'success': True}

@socketio.on('join_user_room')
def handle_join_user_room():
    """Join user's personal room for direct notifications"""
    logger.info(f"Join user room request from {request.sid}")
    
    # Find user_id by socket id
    user_id = None
    for uid, sid in socketio.server.environ.get('socketio', {}).get('rooms', {}).items():
        if sid == request.sid:
            user_id = uid
            break
    
    if not user_id:
        logger.warning(f"Join user room from unauthenticated client: {request.sid}")
        return {'success': False, 'error': 'Not authenticated'}
    
    # Get user from database
    from models import User
    user = User.query.get(user_id)
    if not user:
        logger.warning(f"User {user_id} not found in database")
        return {'success': False, 'error': 'User not found'}

    room_name = f"user_{user.id}"
    join_room(room_name)
    logger.info(f"User {user.username} joined their personal room: {room_name}")
    
    return {'success': True}
