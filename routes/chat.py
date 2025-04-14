import os
import logging
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify
from sqlalchemy import or_, and_

from app import app, db, socketio, save_photo
from models import User, ChatGroup, ChatMember, ChatMessage, MessageReadReceipt, Friend, Notification
from routes.auth import login_required
from flask_socketio import emit, join_room, leave_room

# Set up logger
logger = logging.getLogger(__name__)

# Create Blueprint
chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/messages')
@login_required
def messages():
    return render_template('chat.html')

@chat_bp.route('/api/chats')
@login_required
def get_chats():
    # Get all chat groups where the user is a member
    chat_memberships = ChatMember.query.filter_by(user_id=g.user.id).all()
    chat_ids = [m.chat_id for m in chat_memberships]
    
    # Get the chat groups with the latest message
    chats = []
    for chat_id in chat_ids:
        chat_group = ChatGroup.query.get(chat_id)
        
        # Get the latest message
        latest_message = ChatMessage.query.filter_by(chat_id=chat_id).order_by(ChatMessage.created_at.desc()).first()
        
        # Get unread messages count
        member = ChatMember.query.filter_by(chat_id=chat_id, user_id=g.user.id).first()
        unread_count = 0
        
        if member and member.last_read:
            unread_count = ChatMessage.query.filter(
                ChatMessage.chat_id == chat_id,
                ChatMessage.created_at > member.last_read,
                ChatMessage.user_id != g.user.id
            ).count()
        
        # For direct messages, get the other user's info
        other_user = None
        if not chat_group.is_group:
            other_member = ChatMember.query.filter(
                ChatMember.chat_id == chat_id,
                ChatMember.user_id != g.user.id
            ).first()
            
            if other_member:
                other_user = User.query.get(other_member.user_id)
        
        chat_data = chat_group.serialize()
        chat_data['unread_count'] = unread_count
        
        if other_user:
            chat_data['name'] = other_user.username
            chat_data['profile_pic'] = other_user.profile_pic
        
        chats.append(chat_data)
    
    # Sort chats by latest message
    chats.sort(key=lambda x: x['updated_at'] if 'updated_at' in x else '', reverse=True)
    
    return jsonify({
        'chats': chats
    })

@chat_bp.route('/chat/<int:chat_id>')
@login_required
def view_chat(chat_id):
    # Check if user is a member of this chat
    member = ChatMember.query.filter_by(chat_id=chat_id, user_id=g.user.id).first()
    
    if not member:
        flash('You are not a member of this chat', 'danger')
        return redirect(url_for('chat.messages'))
    
    chat_group = ChatGroup.query.get_or_404(chat_id)
    
    # Update last_read
    member.last_read = datetime.utcnow()
    db.session.commit()
    
    if chat_group.is_group:
        return render_template('chat_group.html', chat=chat_group)
    else:
        # For direct messages, get the other user
        other_member = ChatMember.query.filter(
            ChatMember.chat_id == chat_id,
            ChatMember.user_id != g.user.id
        ).first()
        
        other_user = User.query.get(other_member.user_id) if other_member else None
        
        return render_template('chat.html', chat=chat_group, other_user=other_user)

@chat_bp.route('/api/chat/<int:chat_id>/messages')
@login_required
def get_chat_messages(chat_id):
    # Check if user is a member of this chat
    member = ChatMember.query.filter_by(chat_id=chat_id, user_id=g.user.id).first()
    
    if not member:
        return jsonify({'error': 'You are not a member of this chat'}), 403
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Get messages for the chat with pagination (newest first, then reverse for display)
    messages = ChatMessage.query.filter_by(chat_id=chat_id).order_by(ChatMessage.created_at.desc())
    total_messages = messages.count()
    
    messages = messages.offset((page - 1) * per_page).limit(per_page).all()
    messages.reverse()  # Reverse to show oldest first
    
    # Update last_read
    member.last_read = datetime.utcnow()
    db.session.commit()
    
    # Serialize messages
    serialized_messages = [message.serialize() for message in messages]
    
    return jsonify({
        'messages': serialized_messages,
        'pagination': {
            'current_page': page,
            'per_page': per_page,
            'total_messages': total_messages,
            'total_pages': (total_messages + per_page - 1) // per_page
        }
    })

@chat_bp.route('/api/chat/create', methods=['POST'])
@login_required
def create_chat():
    if request.is_json:
        data = request.get_json()
        is_group = data.get('is_group', False)
        name = data.get('name', '').strip() if is_group else None
        member_ids = data.get('member_ids', [])
        
        # For direct messages, we need exactly one other user
        if not is_group and len(member_ids) != 1:
            return jsonify({'error': 'Direct messages require exactly one recipient'}), 400
        
        # For group chats, we need at least 2 other users (3 total including creator)
        if is_group and len(member_ids) < 2:
            return jsonify({'error': 'Group chats require at least 3 members (including you)'}), 400
        
        # For group chats, we need at most 99 other users (100 total including creator)
        if is_group and len(member_ids) > 99:
            return jsonify({'error': 'Group chats can have at most 100 members (including you)'}), 400
        
        # Check if users exist and are friends with the creator
        for member_id in member_ids:
            user = User.query.get(member_id)
            if not user:
                return jsonify({'error': f'User with ID {member_id} not found'}), 404
            
            # Only for direct messages, check if they are friends
            if not is_group:
                friendship = Friend.query.filter(
                    or_(
                        and_(Friend.user_id == g.user.id, Friend.friend_id == member_id),
                        and_(Friend.user_id == member_id, Friend.friend_id == g.user.id)
                    ),
                    Friend.status == 'accepted'
                ).first()
                
                if not friendship:
                    return jsonify({'error': f'You must be friends with the recipient to start a chat'}), 403
        
        # For direct messages, check if a chat already exists
        if not is_group:
            other_user_id = member_ids[0]
            
            # Look for existing direct message chats between these users
            existing_chats = db.session.query(ChatGroup).join(ChatMember, ChatGroup.id == ChatMember.chat_id).filter(
                ChatGroup.is_group == False,
                ChatMember.user_id == g.user.id
            ).all()
            
            for chat in existing_chats:
                # Check if the other user is also a member
                other_member = ChatMember.query.filter_by(chat_id=chat.id, user_id=other_user_id).first()
                if other_member:
                    # Chat already exists, return it
                    return jsonify({
                        'success': True,
                        'chat': chat.serialize(),
                        'existing': True
                    })
        
        # Create the chat group
        chat_group = ChatGroup(
            name=name,
            created_by=g.user.id,
            is_group=is_group
        )
        db.session.add(chat_group)
        db.session.flush()  # Get chat ID without committing
        
        # Add creator as admin
        creator_member = ChatMember(
            chat_id=chat_group.id,
            user_id=g.user.id,
            role='admin' if is_group else 'member',
            last_read=datetime.utcnow()
        )
        db.session.add(creator_member)
        
        # Add other members
        for member_id in member_ids:
            member = ChatMember(
                chat_id=chat_group.id,
                user_id=member_id,
                role='member',
                last_read=None
            )
            db.session.add(member)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'chat': chat_group.serialize(),
            'existing': False
        })
    else:
        return jsonify({'error': 'Request must be JSON'}), 400

@chat_bp.route('/api/chat/<int:chat_id>/members')
@login_required
def get_chat_members(chat_id):
    # Check if user is a member of this chat
    member = ChatMember.query.filter_by(chat_id=chat_id, user_id=g.user.id).first()
    
    if not member:
        return jsonify({'error': 'You are not a member of this chat'}), 403
    
    # Get all members of the chat
    members = ChatMember.query.filter_by(chat_id=chat_id).all()
    
    # Serialize members
    serialized_members = [member.serialize() for member in members]
    
    return jsonify({
        'members': serialized_members
    })

@chat_bp.route('/api/chat/<int:chat_id>/add_member', methods=['POST'])
@login_required
def add_chat_member(chat_id):
    # Check if user is an admin of this chat
    admin = ChatMember.query.filter_by(chat_id=chat_id, user_id=g.user.id, role='admin').first()
    
    if not admin:
        return jsonify({'error': 'You must be an admin to add members'}), 403
    
    if request.is_json:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        # Check if user exists
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': f'User with ID {user_id} not found'}), 404
        
        # Check if user is already a member
        existing_member = ChatMember.query.filter_by(chat_id=chat_id, user_id=user_id).first()
        if existing_member:
            return jsonify({'error': 'User is already a member of this chat'}), 409
        
        # Get current member count
        member_count = ChatMember.query.filter_by(chat_id=chat_id).count()
        if member_count >= 100:
            return jsonify({'error': 'Chat group has reached maximum member limit (100)'}), 400
        
        # Add user as member
        member = ChatMember(
            chat_id=chat_id,
            user_id=user_id,
            role='member',
            last_read=None
        )
        db.session.add(member)
        db.session.commit()
        
        # Notify the user
        chat_group = ChatGroup.query.get(chat_id)
        notification = Notification(
            user_id=user_id,
            notification_type='chat_invite',
            sender_id=g.user.id,
            reference_id=chat_id,
            content=f"{g.user.username} added you to the chat '{chat_group.name}'"
        )
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'member': member.serialize()
        })
    else:
        return jsonify({'error': 'Request must be JSON'}), 400

@chat_bp.route('/api/chat/<int:chat_id>/remove_member', methods=['POST'])
@login_required
def remove_chat_member(chat_id):
    # Check if user is an admin of this chat
    admin = ChatMember.query.filter_by(chat_id=chat_id, user_id=g.user.id, role='admin').first()
    
    if not admin:
        return jsonify({'error': 'You must be an admin to remove members'}), 403
    
    if request.is_json:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        # Cannot remove self if you're the only admin
        if user_id == g.user.id:
            # Check if there are other admins
            other_admins = ChatMember.query.filter(
                ChatMember.chat_id == chat_id,
                ChatMember.role == 'admin',
                ChatMember.user_id != g.user.id
            ).first()
            
            if not other_admins:
                return jsonify({'error': 'You cannot remove yourself as you are the only admin'}), 400
        
        # Check if user is a member
        member = ChatMember.query.filter_by(chat_id=chat_id, user_id=user_id).first()
        if not member:
            return jsonify({'error': 'User is not a member of this chat'}), 404
        
        # Remove user
        db.session.delete(member)
        db.session.commit()
        
        return jsonify({
            'success': True
        })
    else:
        return jsonify({'error': 'Request must be JSON'}), 400

@chat_bp.route('/api/chat/<int:chat_id>/make_admin', methods=['POST'])
@login_required
def make_chat_admin(chat_id):
    # Check if user is an admin of this chat
    admin = ChatMember.query.filter_by(chat_id=chat_id, user_id=g.user.id, role='admin').first()
    
    if not admin:
        return jsonify({'error': 'You must be an admin to promote members'}), 403
    
    if request.is_json:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        # Check if user is a member
        member = ChatMember.query.filter_by(chat_id=chat_id, user_id=user_id).first()
        if not member:
            return jsonify({'error': 'User is not a member of this chat'}), 404
        
        # Promote to admin
        member.role = 'admin'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'member': member.serialize()
        })
    else:
        return jsonify({'error': 'Request must be JSON'}), 400

@chat_bp.route('/api/chat/<int:chat_id>/leave', methods=['POST'])
@login_required
def leave_chat(chat_id):
    # Check if user is a member of this chat
    member = ChatMember.query.filter_by(chat_id=chat_id, user_id=g.user.id).first()
    
    if not member:
        return jsonify({'error': 'You are not a member of this chat'}), 403
    
    chat_group = ChatGroup.query.get_or_404(chat_id)
    
    # If this is a direct message, we need to handle differently
    if not chat_group.is_group:
        return jsonify({'error': 'You cannot leave a direct message chat'}), 400
    
    # If user is an admin, check if there are other admins
    if member.role == 'admin':
        other_admins = ChatMember.query.filter(
            ChatMember.chat_id == chat_id,
            ChatMember.role == 'admin',
            ChatMember.user_id != g.user.id
        ).first()
        
        # If no other admins, promote someone else if possible
        if not other_admins:
            other_member = ChatMember.query.filter(
                ChatMember.chat_id == chat_id,
                ChatMember.user_id != g.user.id
            ).first()
            
            if other_member:
                other_member.role = 'admin'
                db.session.commit()
    
    # Leave the chat
    db.session.delete(member)
    db.session.commit()
    
    return jsonify({
        'success': True
    })

# Socket.IO event handlers
@socketio.on('connect')
def handle_connect():
    if g.user:
        logger.debug(f"User {g.user.id} connected to Socket.IO")
        
        # Join all chat rooms that the user is a member of
        chat_memberships = ChatMember.query.filter_by(user_id=g.user.id).all()
        for membership in chat_memberships:
            join_room(f'chat_{membership.chat_id}')
        
        # Join user's personal notification room
        join_room(f'user_{g.user.id}')
    else:
        logger.debug("Anonymous user connected to Socket.IO")

@socketio.on('disconnect')
def handle_disconnect():
    if g.user:
        logger.debug(f"User {g.user.id} disconnected from Socket.IO")
    else:
        logger.debug("Anonymous user disconnected from Socket.IO")

@socketio.on('join_chat')
def handle_join_chat(data):
    chat_id = data.get('chat_id')
    
    if not g.user:
        return
    
    # Check if user is a member of this chat
    member = ChatMember.query.filter_by(chat_id=chat_id, user_id=g.user.id).first()
    
    if member:
        join_room(f'chat_{chat_id}')
        logger.debug(f"User {g.user.id} joined room chat_{chat_id}")
        
        # Update last_read
        member.last_read = datetime.utcnow()
        db.session.commit()

@socketio.on('leave_chat')
def handle_leave_chat(data):
    chat_id = data.get('chat_id')
    
    if not g.user:
        return
    
    leave_room(f'chat_{chat_id}')
    logger.debug(f"User {g.user.id} left room chat_{chat_id}")

@socketio.on('send_message')
def handle_send_message(data):
    chat_id = data.get('chat_id')
    content = data.get('content', '').strip()
    message_type = data.get('message_type', 'text')
    
    if not g.user:
        return {'error': 'You must be logged in'}
    
    # Check if user is a member of this chat
    member = ChatMember.query.filter_by(chat_id=chat_id, user_id=g.user.id).first()
    
    if not member:
        return {'error': 'You are not a member of this chat'}
    
    # Create message
    message = ChatMessage(
        chat_id=chat_id,
        user_id=g.user.id,
        message_type=message_type,
        content=content,
        is_deleted=False
    )
    db.session.add(message)
    
    # Update chat group's updated_at
    chat_group = ChatGroup.query.get(chat_id)
    chat_group.updated_at = datetime.utcnow()
    
    # Update sender's last_read
    member.last_read = datetime.utcnow()
    
    db.session.commit()
    
    # Emit message to all members of the chat
    emit('new_message', message.serialize(), room=f'chat_{chat_id}')
    
    # Create notifications for other members
    other_members = ChatMember.query.filter(
        ChatMember.chat_id == chat_id,
        ChatMember.user_id != g.user.id
    ).all()
    
    chat_name = chat_group.name
    if not chat_group.is_group:
        # For direct messages, use sender's username
        chat_name = g.user.username
    
    for member in other_members:
        # Create notification for this member
        notification = Notification(
            user_id=member.user_id,
            notification_type='message',
            sender_id=g.user.id,
            reference_id=chat_id,
            content=f"{g.user.username}: {content[:50]}..." if len(content) > 50 else f"{g.user.username}: {content}"
        )
        db.session.add(notification)
        
        # Emit notification to this member
        emit('new_notification', notification.serialize(), room=f'user_{member.user_id}')
    
    db.session.commit()
    
    return {'success': True, 'message': message.serialize()}

@socketio.on('delete_message')
def handle_delete_message(data):
    message_id = data.get('message_id')
    
    if not g.user:
        return {'error': 'You must be logged in'}
    
    # Get the message
    message = ChatMessage.query.get(message_id)
    
    if not message:
        return {'error': 'Message not found'}
    
    # Check if user is the sender or an admin of the chat
    if message.user_id != g.user.id:
        # Check if user is an admin
        admin = ChatMember.query.filter_by(chat_id=message.chat_id, user_id=g.user.id, role='admin').first()
        if not admin:
            return {'error': 'You can only delete your own messages'}
    
    # Mark as deleted
    message.is_deleted = True
    message.content = "This message was deleted"
    message.media_url = None
    db.session.commit()
    
    # Emit message update to all members of the chat
    emit('message_deleted', message.serialize(), room=f'chat_{message.chat_id}')
    
    return {'success': True}

@socketio.on('read_messages')
def handle_read_messages(data):
    chat_id = data.get('chat_id')
    
    if not g.user:
        return {'error': 'You must be logged in'}
    
    # Check if user is a member of this chat
    member = ChatMember.query.filter_by(chat_id=chat_id, user_id=g.user.id).first()
    
    if not member:
        return {'error': 'You are not a member of this chat'}
    
    # Update last_read
    member.last_read = datetime.utcnow()
    db.session.commit()
    
    # Mark all messages as read by this user
    unread_messages = ChatMessage.query.filter(
        ChatMessage.chat_id == chat_id,
        ChatMessage.user_id != g.user.id,
        ~ChatMessage.read_receipts.any(MessageReadReceipt.user_id == g.user.id)
    ).all()
    
    for message in unread_messages:
        receipt = MessageReadReceipt(message_id=message.id, user_id=g.user.id)
        db.session.add(receipt)
    
    db.session.commit()
    
    # Notify other chat members about the read status
    read_data = {
        'chat_id': chat_id,
        'user_id': g.user.id,
        'username': g.user.username,
        'read_at': datetime.utcnow().isoformat()
    }
    
    emit('messages_read', read_data, room=f'chat_{chat_id}')
    
    return {'success': True}

# Register the blueprint with the app
app.register_blueprint(chat_bp)
