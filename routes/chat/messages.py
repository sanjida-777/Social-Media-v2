import logging
from datetime import datetime
from flask import render_template, g, request, jsonify, abort
from sqlalchemy import desc

from database import db
from models import User, ChatGroup, ChatMember, ChatMessage, MessageReadReceipt
from routes.auth_old import login_required
from routes.chat import chat_bp

# Set up logger
logger = logging.getLogger(__name__)

@chat_bp.route('/')
@login_required
def messages():
    """Chat interface showing all conversations"""
    return render_template('messaging/chat_index.html')

@chat_bp.route('/<int:chat_id>')
@login_required
def view_chat(chat_id):
    """View a specific chat"""
    # Check if user is a member of this chat
    member = ChatMember.query.filter_by(
        chat_id=chat_id,
        user_id=g.user.id
    ).first()

    if not member:
        abort(403)

    chat = ChatGroup.query.get_or_404(chat_id)

    return render_template('messaging/chat_view.html', chat=chat)

@chat_bp.route('/api/chats')
@login_required
def get_chats():
    """Get all chats for the current user"""
    # Get all chat groups where user is a member
    memberships = ChatMember.query.filter_by(user_id=g.user.id).all()
    chat_ids = [membership.chat_id for membership in memberships]

    chats = ChatGroup.query.filter(ChatGroup.id.in_(chat_ids)).all()

    result = []
    for chat in chats:
        # Get last message
        last_message = ChatMessage.query.filter_by(
            chat_id=chat.id,
            is_deleted=False
        ).order_by(desc(ChatMessage.created_at)).first()

        # Get unread count
        member = ChatMember.query.filter_by(
            chat_id=chat.id,
            user_id=g.user.id
        ).first()

        unread_count = 0
        if member and member.last_read:
            unread_count = ChatMessage.query.filter(
                ChatMessage.chat_id == chat.id,
                ChatMessage.created_at > member.last_read,
                ChatMessage.user_id != g.user.id,
                ChatMessage.is_deleted == False
            ).count()

        # Check if this is a direct message
        other_user = None
        if not chat.is_group:
            other_member = ChatMember.query.filter(
                ChatMember.chat_id == chat.id,
                ChatMember.user_id != g.user.id
            ).first()

            if other_member:
                other_user = User.query.get(other_member.user_id)

        chat_data = {
            'id': chat.id,
            'name': chat.name,
            'is_group': chat.is_group,
            'created_at': chat.created_at.isoformat(),
            'unread_count': unread_count,
            'last_message': last_message.serialize() if last_message else None,
            'other_user': other_user.serialize() if other_user else None
        }

        result.append(chat_data)

    return jsonify(result)

@chat_bp.route('/api/chats/<int:chat_id>/messages')
@login_required
def get_chat_messages(chat_id):
    """Get messages for a specific chat"""
    # Check if user is a member of this chat
    member = ChatMember.query.filter_by(
        chat_id=chat_id,
        user_id=g.user.id
    ).first()

    if not member:
        return jsonify({'error': 'Unauthorized'}), 403

    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # Get messages with pagination
    messages = ChatMessage.query.filter_by(
        chat_id=chat_id,
        is_deleted=False
    ).order_by(desc(ChatMessage.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Update last read timestamp
    member.last_read = datetime.utcnow()
    db.session.commit()

    # Format response
    result = {
        'messages': [message.serialize() for message in messages.items],
        'pagination': {
            'page': messages.page,
            'per_page': messages.per_page,
            'total': messages.total,
            'pages': messages.pages,
            'has_next': messages.has_next,
            'has_prev': messages.has_prev
        }
    }

    return jsonify(result)

@chat_bp.route('/api/chats/<int:chat_id>/messages/send', methods=['POST'])
@login_required
def handle_send_message(chat_id):
    """Send a message to a chat"""
    # Check if user is a member of this chat
    member = ChatMember.query.filter_by(
        chat_id=chat_id,
        user_id=g.user.id
    ).first()

    if not member:
        return jsonify({'error': 'Not a member of this chat'}), 403

    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    content = data.get('content')
    message_type = data.get('type', 'text')
    media_url = data.get('media_url')

    if not content and not media_url:
        return jsonify({'error': 'Message cannot be empty'}), 400

    # Create message in database
    message = ChatMessage(
        chat_id=chat_id,
        user_id=g.user.id,
        message_type=message_type,
        content=content,
        media_url=media_url
    )
    db.session.add(message)
    db.session.flush()  # Get message ID without committing

    # Update last read timestamp for sending user
    member.last_read = datetime.utcnow()
    db.session.commit()

    # Get MQTT client and publish message
    from routes.chat.realtime import get_chat_mqtt_client, get_chat_topic
    client = get_chat_mqtt_client()
    topic = get_chat_topic(chat_id)

    message_payload = {
        'type': 'message',
        'message_id': message.id,
        'chat_id': chat_id,
        'user': {
            'id': g.user.id,
            'username': g.user.username,
            'profile_pic': g.user.profile_pic
        },
        'message_type': message_type,
        'content': content,
        'media_url': media_url,
        'created_at': message.created_at.isoformat(),
        'is_deleted': False
    }

    client.publish(topic, message_payload)

    return jsonify(message.serialize())

@chat_bp.route('/api/chats/<int:chat_id>/messages/<int:message_id>/delete', methods=['POST'])
@login_required
def handle_delete_message(chat_id, message_id):
    """Delete a message"""
    # Check if message exists and belongs to this user
    message = ChatMessage.query.filter_by(
        id=message_id,
        chat_id=chat_id
    ).first()

    if not message:
        return jsonify({'error': 'Message not found'}), 404

    # Only message author or chat admin can delete messages
    is_author = message.user_id == g.user.id
    is_admin = ChatMember.query.filter_by(
        chat_id=chat_id,
        user_id=g.user.id,
        role='admin'
    ).first() is not None

    if not (is_author or is_admin):
        return jsonify({'error': 'Unauthorized'}), 403

    # Soft delete message
    message.is_deleted = True
    message.content = "[This message was deleted]"
    message.media_url = None
    db.session.commit()

    # Send delete notification via MQTT
    from routes.chat.realtime import get_chat_mqtt_client, get_chat_topic
    client = get_chat_mqtt_client()
    topic = get_chat_topic(chat_id)

    delete_payload = {
        'type': 'delete',
        'message_id': message_id,
        'chat_id': chat_id,
        'user_id': g.user.id,
        'username': g.user.username,
        'timestamp': datetime.utcnow().isoformat()
    }

    client.publish(topic, delete_payload)

    return jsonify({'success': True})

@chat_bp.route('/api/chats/<int:chat_id>/messages/read', methods=['POST'])
@login_required
def handle_read_messages(chat_id):
    """Mark messages as read"""
    # Check if user is a member of this chat
    member = ChatMember.query.filter_by(
        chat_id=chat_id,
        user_id=g.user.id
    ).first()

    if not member:
        return jsonify({'error': 'Not a member of this chat'}), 403

    data = request.json
    if not data or not data.get('message_ids'):
        return jsonify({'error': 'No message IDs provided'}), 400

    message_ids = data.get('message_ids')

    # Mark messages as read
    for message_id in message_ids:
        # Check if read receipt already exists
        receipt = MessageReadReceipt.query.filter_by(
            message_id=message_id,
            user_id=g.user.id
        ).first()

        if not receipt:
            # Create read receipt
            receipt = MessageReadReceipt(
                message_id=message_id,
                user_id=g.user.id
            )
            db.session.add(receipt)

    # Update last read timestamp
    member.last_read = datetime.utcnow()
    db.session.commit()

    # Send read notification via MQTT
    from routes.chat.realtime import get_chat_mqtt_client, get_chat_topic
    client = get_chat_mqtt_client()
    topic = get_chat_topic(chat_id)

    read_payload = {
        'type': 'read',
        'message_ids': message_ids,
        'chat_id': chat_id,
        'user_id': g.user.id,
        'username': g.user.username,
        'timestamp': datetime.utcnow().isoformat()
    }

    client.publish(topic, read_payload)

    return jsonify({'success': True})
