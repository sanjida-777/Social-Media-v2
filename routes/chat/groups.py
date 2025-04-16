import logging
from datetime import datetime
from flask import g, request, jsonify

from database import db
from models import User, ChatGroup, ChatMember, ChatMessage
from routes.auth_old import login_required
from routes.chat import chat_bp

# Set up logger
logger = logging.getLogger(__name__)

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
