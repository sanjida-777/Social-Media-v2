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

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")

    # Check if user is authenticated
    if not g.user:
        logger.warning(f"Unauthenticated connection attempt: {request.sid}")
        return False

    logger.info(f"User {g.user.username} connected with session ID: {request.sid}")

    # Update user's online status
    g.user.is_active = True
    g.user.last_online = datetime.now(timezone.utc)
    db.session.commit()

    # Broadcast user's online status to friends
    emit('user_status', {
        'user_id': g.user.id,
        'username': g.user.username,
        'status': 'online'
    }, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")

    if g.user:
        # Update user's online status
        g.user.is_active = False
        g.user.last_online = datetime.now(timezone.utc)
        db.session.commit()

        # Broadcast user's offline status to friends
        emit('user_status', {
            'user_id': g.user.id,
            'username': g.user.username,
            'status': 'offline'
        }, broadcast=True)

@socketio.on('join_conversation')
def handle_join_conversation(data):
    """Join a conversation room"""
    if not g.user:
        return

    conversation_id = data.get('conversation_id')
    if not conversation_id:
        return

    # Check if user is part of this conversation
    conversation = Conversation.query.get(conversation_id)
    if not conversation:
        return

    if conversation.user1_id != g.user.id and conversation.user2_id != g.user.id:
        logger.warning(f"User {g.user.username} attempted to join conversation {conversation_id} they're not part of")
        return

    # Join the room
    room_name = f"conversation_{conversation_id}"
    join_room(room_name)
    logger.info(f"User {g.user.username} joined room: {room_name}")

    # Mark messages as read
    unread_messages = Message.query.filter_by(
        conversation_id=conversation_id,
        recipient_id=g.user.id,
        read=False
    ).all()

    for message in unread_messages:
        message.read = True

    db.session.commit()

    # Notify the other user that messages have been read
    other_user_id = conversation.user2_id if conversation.user1_id == g.user.id else conversation.user1_id
    emit('messages_read', {
        'conversation_id': conversation_id,
        'user_id': g.user.id
    }, room=f"user_{other_user_id}")

@socketio.on('leave_conversation')
def handle_leave_conversation(data):
    """Leave a conversation room"""
    if not g.user:
        return

    conversation_id = data.get('conversation_id')
    if not conversation_id:
        return

    # Leave the room
    room_name = f"conversation_{conversation_id}"
    leave_room(room_name)
    logger.info(f"User {g.user.username} left room: {room_name}")

@socketio.on('send_message')
def handle_send_message(data):
    """Handle new message"""
    if not g.user:
        return {'success': False, 'error': 'Not authenticated'}

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
        ((Conversation.user1_id == g.user.id) & (Conversation.user2_id == recipient.id)) |
        ((Conversation.user1_id == recipient.id) & (Conversation.user2_id == g.user.id))
    ).first()

    if not conversation:
        conversation = Conversation(
            user1_id=g.user.id,
            user2_id=recipient.id
        )
        db.session.add(conversation)
        db.session.commit()

    # Create message
    message = Message(
        conversation_id=conversation.id,
        sender_id=g.user.id,
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
        'sender_username': g.user.username,
        'sender_profile_pic': g.user.profile_pic,
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
    if not g.user:
        return

    conversation_id = data.get('conversation_id')
    if not conversation_id:
        return

    # Check if user is part of this conversation
    conversation = Conversation.query.get(conversation_id)
    if not conversation:
        return

    if conversation.user1_id != g.user.id and conversation.user2_id != g.user.id:
        return

    # Emit typing event to conversation room
    room_name = f"conversation_{conversation_id}"
    emit('typing', {
        'user_id': g.user.id,
        'username': g.user.username,
        'conversation_id': conversation_id
    }, room=room_name, include_self=False)

@socketio.on('join_user_room')
def handle_join_user_room():
    """Join user's personal room for direct notifications"""
    if not g.user:
        return

    room_name = f"user_{g.user.id}"
    join_room(room_name)
    logger.info(f"User {g.user.username} joined their personal room: {room_name}")
