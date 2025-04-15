import logging
from datetime import datetime
from flask import render_template, redirect, url_for, request, g, jsonify
from database import db
from models import User, Message, Conversation
from routes.auth import auth_bp

# Set up logger
logger = logging.getLogger(__name__)

@auth_bp.route('/messages')
def messages_redirect():
    """Redirect to messages inbox"""
    return redirect(url_for('auth.messages_inbox'))

@auth_bp.route('/messages/inbox')
def messages_inbox():
    """Messages inbox page"""
    if not g.user:
        return redirect(url_for('auth.login'))

    # Get all conversations for the current user
    conversations = []

    # Get conversations where user is user1
    user1_convos = Conversation.query.filter_by(user1_id=g.user.id).all()
    for convo in user1_convos:
        # Get the other user
        other_user = User.query.get(convo.user2_id)
        if other_user:
            # Get the last message
            last_message = Message.query.filter_by(conversation_id=convo.id).order_by(Message.created_at.desc()).first()

            # Get unread count
            unread_count = Message.query.filter_by(
                conversation_id=convo.id,
                recipient_id=g.user.id,
                read=False
            ).count()

            conversations.append({
                'id': convo.id,
                'user': other_user,
                'last_message': last_message,
                'unread_count': unread_count
            })

    # Get conversations where user is user2
    user2_convos = Conversation.query.filter_by(user2_id=g.user.id).all()
    for convo in user2_convos:
        # Get the other user
        other_user = User.query.get(convo.user1_id)
        if other_user:
            # Get the last message
            last_message = Message.query.filter_by(conversation_id=convo.id).order_by(Message.created_at.desc()).first()

            # Get unread count
            unread_count = Message.query.filter_by(
                conversation_id=convo.id,
                recipient_id=g.user.id,
                read=False
            ).count()

            conversations.append({
                'id': convo.id,
                'user': other_user,
                'last_message': last_message,
                'unread_count': unread_count
            })

    # Sort conversations by last message time
    conversations.sort(key=lambda x: x['last_message'].created_at if x['last_message'] else datetime.min, reverse=True)

    return render_template('messaging/inbox.html', conversations=conversations)

@auth_bp.route('/messages/<username>')
def messages(username):
    """Messages page for a specific user"""
    if not g.user:
        return redirect(url_for('auth.login'))

    # Get the other user
    other_user = User.query.filter_by(username=username).first_or_404()

    # Find or create conversation
    conversation = Conversation.query.filter(
        ((Conversation.user1_id == g.user.id) & (Conversation.user2_id == other_user.id)) |
        ((Conversation.user1_id == other_user.id) & (Conversation.user2_id == g.user.id))
    ).first()

    if not conversation:
        conversation = Conversation(
            user1_id=g.user.id,
            user2_id=other_user.id
        )
        db.session.add(conversation)
        db.session.commit()

    # Get messages
    messages = Message.query.filter_by(conversation_id=conversation.id).order_by(Message.created_at).all()

    # Mark messages as read
    unread_messages = Message.query.filter_by(
        conversation_id=conversation.id,
        recipient_id=g.user.id,
        read=False
    ).all()

    for message in unread_messages:
        message.read = True

    db.session.commit()

    return render_template('messaging/messages.html', other_user=other_user, messages=messages, conversation_id=conversation.id)

@auth_bp.route('/api/messages/send', methods=['POST'])
def send_message():
    """API endpoint to send a message"""
    if not g.user:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    data = request.get_json()
    if not data or 'recipient_id' not in data or 'content' not in data:
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400

    recipient_id = data['recipient_id']
    content = data['content']

    # Get recipient
    recipient = User.query.get(recipient_id)
    if not recipient:
        return jsonify({'success': False, 'message': 'Recipient not found'}), 404

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
        created_at=datetime.now()
    )
    db.session.add(message)

    # Update conversation last_message_at
    conversation.last_message_at = message.created_at
    db.session.commit()

    return jsonify({
        'success': True,
        'message': {
            'id': message.id,
            'content': message.content,
            'created_at': message.created_at.isoformat()
        }
    })

@auth_bp.route('/api/messages/read', methods=['POST'])
def mark_messages_read():
    """API endpoint to mark messages as read"""
    if not g.user:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    data = request.get_json()
    if not data or 'conversation_id' not in data:
        return jsonify({'success': False, 'message': 'Missing conversation_id'}), 400

    conversation_id = data['conversation_id']

    # Check if user is part of this conversation
    conversation = Conversation.query.get(conversation_id)
    if not conversation:
        return jsonify({'success': False, 'message': 'Conversation not found'}), 404

    if conversation.user1_id != g.user.id and conversation.user2_id != g.user.id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403

    # Mark messages as read
    unread_messages = Message.query.filter_by(
        conversation_id=conversation_id,
        recipient_id=g.user.id,
        read=False
    ).all()

    for message in unread_messages:
        message.read = True

    db.session.commit()

    return jsonify({'success': True, 'count': len(unread_messages)})
