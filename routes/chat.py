import json
import time
import logging
from datetime import datetime
from urllib.parse import quote_plus
from flask import Blueprint, render_template, g, request, jsonify, abort
from sqlalchemy import desc

from app import db
from models import User, ChatGroup, ChatMember, ChatMessage, MessageReadReceipt
from utils.mqtt_client import get_mqtt_client
from routes.auth import login_required

# Set up logger
logger = logging.getLogger(__name__)

# Create blueprint
chat_bp = Blueprint('chat', __name__, url_prefix='/chat')

@chat_bp.route('/')
@login_required
def messages():
    """Chat interface showing all conversations"""
    return render_template('chat/index.html')

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
    
    return render_template('chat/view.html', chat=chat)

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

@chat_bp.route('/api/chats/create', methods=['POST'])
@login_required
def create_chat():
    """Create a new chat"""
    data = request.json
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Check required fields
    if data.get('is_group') and not data.get('name'):
        return jsonify({'error': 'Group chats require a name'}), 400
    
    if not data.get('is_group') and not data.get('user_id'):
        return jsonify({'error': 'Direct messages require a user ID'}), 400
    
    # If direct message, check if chat already exists
    if not data.get('is_group'):
        other_user_id = data.get('user_id')
        other_user = User.query.get(other_user_id)
        
        if not other_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check for existing direct message chat
        existing_chats = db.session.query(ChatGroup).join(
            ChatMember, ChatGroup.id == ChatMember.chat_id
        ).filter(
            ChatGroup.is_group == False,
            ChatMember.user_id == g.user.id
        ).all()
        
        for chat in existing_chats:
            # Check if other user is also a member
            other_member = ChatMember.query.filter_by(
                chat_id=chat.id,
                user_id=other_user_id
            ).first()
            
            if other_member:
                return jsonify({'id': chat.id})
        
        # Create new direct message chat
        chat_name = f"{g.user.username}, {other_user.username}"
        chat = ChatGroup(
            name=chat_name,
            created_by=g.user.id,
            is_group=False
        )
        
        db.session.add(chat)
        db.session.flush()  # Get chat ID without committing
        
        # Add members
        members = [
            ChatMember(chat_id=chat.id, user_id=g.user.id, role='admin'),
            ChatMember(chat_id=chat.id, user_id=other_user_id, role='member')
        ]
        db.session.add_all(members)
        db.session.commit()
        
        return jsonify({'id': chat.id})
    
    # Create group chat
    chat = ChatGroup(
        name=data.get('name'),
        created_by=g.user.id,
        is_group=True
    )
    
    db.session.add(chat)
    db.session.flush()  # Get chat ID without committing
    
    # Add creator as admin
    member = ChatMember(
        chat_id=chat.id,
        user_id=g.user.id,
        role='admin'
    )
    db.session.add(member)
    
    # Add other members if provided
    if data.get('members'):
        for user_id in data.get('members'):
            if user_id != g.user.id:  # Skip creator
                user = User.query.get(user_id)
                if user:
                    member = ChatMember(
                        chat_id=chat.id,
                        user_id=user_id,
                        role='member'
                    )
                    db.session.add(member)
    
    db.session.commit()
    
    return jsonify({'id': chat.id})

@chat_bp.route('/api/chats/<int:chat_id>/members')
@login_required
def get_chat_members(chat_id):
    """Get members of a chat"""
    # Check if user is a member of this chat
    member = ChatMember.query.filter_by(
        chat_id=chat_id,
        user_id=g.user.id
    ).first()
    
    if not member:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get all members
    members = ChatMember.query.filter_by(chat_id=chat_id).all()
    
    result = []
    for member in members:
        user = User.query.get(member.user_id)
        if user:
            result.append({
                'user': user.serialize(),
                'role': member.role,
                'joined_at': member.joined_at.isoformat()
            })
    
    return jsonify(result)

@chat_bp.route('/api/chats/<int:chat_id>/members/add', methods=['POST'])
@login_required
def add_chat_member(chat_id):
    """Add a member to a chat"""
    # Check if user is an admin of this chat
    member = ChatMember.query.filter_by(
        chat_id=chat_id,
        user_id=g.user.id,
        role='admin'
    ).first()
    
    if not member:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Check if chat is a group
    chat = ChatGroup.query.get_or_404(chat_id)
    if not chat.is_group:
        return jsonify({'error': 'Cannot add members to direct messages'}), 400
    
    data = request.json
    if not data or not data.get('user_id'):
        return jsonify({'error': 'No user ID provided'}), 400
    
    user_id = data.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if user is already a member
    existing_member = ChatMember.query.filter_by(
        chat_id=chat_id,
        user_id=user_id
    ).first()
    
    if existing_member:
        return jsonify({'error': 'User is already a member'}), 400
    
    # Add new member
    new_member = ChatMember(
        chat_id=chat_id,
        user_id=user_id,
        role='member'
    )
    db.session.add(new_member)
    db.session.commit()
    
    # Create system message
    system_message = ChatMessage(
        chat_id=chat_id,
        user_id=g.user.id,
        message_type='system',
        content=f"{g.user.username} added {user.username} to the chat"
    )
    db.session.add(system_message)
    db.session.commit()
    
    return jsonify({'success': True})

@chat_bp.route('/api/chats/<int:chat_id>/members/remove', methods=['POST'])
@login_required
def remove_chat_member(chat_id):
    """Remove a member from a chat"""
    # Check if user is an admin of this chat
    member = ChatMember.query.filter_by(
        chat_id=chat_id,
        user_id=g.user.id,
        role='admin'
    ).first()
    
    if not member:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Check if chat is a group
    chat = ChatGroup.query.get_or_404(chat_id)
    if not chat.is_group:
        return jsonify({'error': 'Cannot remove members from direct messages'}), 400
    
    data = request.json
    if not data or not data.get('user_id'):
        return jsonify({'error': 'No user ID provided'}), 400
    
    user_id = data.get('user_id')
    
    # Cannot remove self
    if user_id == g.user.id:
        return jsonify({'error': 'Cannot remove yourself from the chat'}), 400
    
    # Check if user is a member
    member_to_remove = ChatMember.query.filter_by(
        chat_id=chat_id,
        user_id=user_id
    ).first()
    
    if not member_to_remove:
        return jsonify({'error': 'User is not a member of this chat'}), 400
    
    # Get user for system message
    user = User.query.get(user_id)
    
    # Remove member
    db.session.delete(member_to_remove)
    
    # Create system message
    system_message = ChatMessage(
        chat_id=chat_id,
        user_id=g.user.id,
        message_type='system',
        content=f"{g.user.username} removed {user.username} from the chat"
    )
    db.session.add(system_message)
    db.session.commit()
    
    return jsonify({'success': True})

@chat_bp.route('/api/chats/<int:chat_id>/admin', methods=['POST'])
@login_required
def make_chat_admin(chat_id):
    """Make a user an admin of a chat"""
    # Check if user is an admin of this chat
    member = ChatMember.query.filter_by(
        chat_id=chat_id,
        user_id=g.user.id,
        role='admin'
    ).first()
    
    if not member:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Check if chat is a group
    chat = ChatGroup.query.get_or_404(chat_id)
    if not chat.is_group:
        return jsonify({'error': 'Cannot change admin status in direct messages'}), 400
    
    data = request.json
    if not data or not data.get('user_id'):
        return jsonify({'error': 'No user ID provided'}), 400
    
    user_id = data.get('user_id')
    
    # Check if user is a member
    member_to_promote = ChatMember.query.filter_by(
        chat_id=chat_id,
        user_id=user_id
    ).first()
    
    if not member_to_promote:
        return jsonify({'error': 'User is not a member of this chat'}), 400
    
    # Already an admin
    if member_to_promote.role == 'admin':
        return jsonify({'error': 'User is already an admin'}), 400
    
    # Get user for system message
    user = User.query.get(user_id)
    
    # Promote to admin
    member_to_promote.role = 'admin'
    
    # Create system message
    system_message = ChatMessage(
        chat_id=chat_id,
        user_id=g.user.id,
        message_type='system',
        content=f"{g.user.username} made {user.username} an admin"
    )
    db.session.add(system_message)
    db.session.commit()
    
    return jsonify({'success': True})

@chat_bp.route('/api/chats/<int:chat_id>/leave', methods=['POST'])
@login_required
def leave_chat(chat_id):
    """Leave a chat"""
    # Check if user is a member of this chat
    member = ChatMember.query.filter_by(
        chat_id=chat_id,
        user_id=g.user.id
    ).first()
    
    if not member:
        return jsonify({'error': 'Not a member of this chat'}), 403
    
    # Check if chat is a group
    chat = ChatGroup.query.get_or_404(chat_id)
    if not chat.is_group:
        return jsonify({'error': 'Cannot leave direct messages'}), 400
    
    # Check if user is the only admin
    if member.role == 'admin':
        admin_count = ChatMember.query.filter_by(
            chat_id=chat_id,
            role='admin'
        ).count()
        
        if admin_count == 1:
            # Find another member to promote
            other_member = ChatMember.query.filter(
                ChatMember.chat_id == chat_id,
                ChatMember.user_id != g.user.id
            ).first()
            
            if other_member:
                other_member.role = 'admin'
            else:
                # No other members, delete the chat
                chat_messages = ChatMessage.query.filter_by(chat_id=chat_id).all()
                for message in chat_messages:
                    db.session.delete(message)
                
                db.session.delete(chat)
                db.session.delete(member)
                db.session.commit()
                
                return jsonify({'success': True})
    
    # Create system message
    system_message = ChatMessage(
        chat_id=chat_id,
        user_id=g.user.id,
        message_type='system',
        content=f"{g.user.username} left the chat"
    )
    db.session.add(system_message)
    
    # Remove user from chat
    db.session.delete(member)
    db.session.commit()
    
    return jsonify({'success': True})

# MQTT-based real-time chat

# Initialize MQTT client for the module
mqtt_client = None

def get_chat_mqtt_client():
    """Get or create the MQTT client for chat"""
    global mqtt_client
    if mqtt_client is None:
        mqtt_client = get_mqtt_client('socialconnect_chat')
    return mqtt_client

def get_chat_topic(chat_id):
    """Get the MQTT topic for a chat"""
    return f"socialconnect/chat/{chat_id}"

@chat_bp.route('/api/mqtt/connect', methods=['POST'])
@login_required
def handle_connect():
    """Connect to MQTT broker"""
    client = get_chat_mqtt_client()
    
    # Connection handled internally in get_mqtt_client
    if client.connected:
        return jsonify({'success': True})
    else:
        success = client.connect()
        return jsonify({'success': success})

@chat_bp.route('/api/mqtt/disconnect', methods=['POST'])
@login_required
def handle_disconnect():
    """Disconnect from MQTT broker"""
    client = get_chat_mqtt_client()
    client.disconnect()
    return jsonify({'success': True})

@chat_bp.route('/api/mqtt/join', methods=['POST'])
@login_required
def handle_join_chat(chat_id=None):
    """Join a chat's MQTT topic"""
    data = request.json
    if not data and not chat_id:
        return jsonify({'error': 'No chat ID provided'}), 400
    
    chat_id = chat_id or data.get('chat_id')
    if not chat_id:
        return jsonify({'error': 'No chat ID provided'}), 400
    
    # Check if user is a member of this chat
    member = ChatMember.query.filter_by(
        chat_id=chat_id,
        user_id=g.user.id
    ).first()
    
    if not member:
        return jsonify({'error': 'Not a member of this chat'}), 403
    
    # Subscribe to chat topic
    client = get_chat_mqtt_client()
    topic = get_chat_topic(chat_id)
    
    def on_message(payload):
        """Handle incoming MQTT messages (for testing)"""
        logger.debug(f"Received MQTT message on topic {topic}: {payload}")
    
    success = client.subscribe(topic, on_message)
    
    # Update presence status
    presence_payload = {
        'type': 'presence',
        'action': 'join',
        'user_id': g.user.id,
        'username': g.user.username,
        'timestamp': datetime.utcnow().isoformat()
    }
    client.publish(topic, presence_payload)
    
    return jsonify({'success': success})

@chat_bp.route('/api/mqtt/leave', methods=['POST'])
@login_required
def handle_leave_chat(chat_id=None):
    """Leave a chat's MQTT topic"""
    data = request.json
    if not data and not chat_id:
        return jsonify({'error': 'No chat ID provided'}), 400
    
    chat_id = chat_id or data.get('chat_id')
    if not chat_id:
        return jsonify({'error': 'No chat ID provided'}), 400
    
    # Unsubscribe from chat topic
    client = get_chat_mqtt_client()
    topic = get_chat_topic(chat_id)
    
    # Update presence status before unsubscribing
    presence_payload = {
        'type': 'presence',
        'action': 'leave',
        'user_id': g.user.id,
        'username': g.user.username,
        'timestamp': datetime.utcnow().isoformat()
    }
    client.publish(topic, presence_payload)
    
    success = client.unsubscribe(topic)
    
    return jsonify({'success': success})

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
    
    # Send message via MQTT
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