import logging
from flask import jsonify, request, g
from models import User, Message, Conversation
from routes.api import api_bp
from database import db
from datetime import datetime

# Set up logger
logger = logging.getLogger(__name__)

@api_bp.route('/messages/send', methods=['POST'])
def send_message():
    """Send a message to another user"""
    try:
        if not g.user:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401

        # Get JSON data
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        recipient_id = data.get('recipient_id')
        recipient_username = data.get('recipient_username')
        content = data.get('content')

        if not content:
            return jsonify({
                'success': False,
                'error': 'Message content is required'
            }), 400

        # Find recipient
        recipient = None
        if recipient_id:
            recipient = User.query.get(recipient_id)
        elif recipient_username:
            recipient = User.query.filter_by(username=recipient_username).first()
        else:
            return jsonify({
                'success': False,
                'error': 'Recipient ID or username is required'
            }), 400

        if not recipient:
            return jsonify({
                'success': False,
                'error': 'Recipient not found'
            }), 404

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
            created_at=datetime.utcnow()
        )
        db.session.add(message)
        db.session.commit()

        # Update conversation last_message_at
        conversation.last_message_at = message.created_at
        db.session.commit()

        return jsonify({
            'success': True,
            'message': {
                'id': message.id,
                'conversation_id': message.conversation_id,
                'sender_id': message.sender_id,
                'recipient_id': message.recipient_id,
                'content': message.content,
                'created_at': message.created_at.isoformat(),
                'read': message.read
            }
        })

    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while sending the message'
        }), 500

@api_bp.route('/messages/<int:conversation_id>', methods=['GET'])
def get_messages(conversation_id):
    """Get messages for a conversation"""
    try:
        if not g.user:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401

        # Get conversation
        conversation = Conversation.query.get(conversation_id)
        if not conversation:
            return jsonify({
                'success': False,
                'error': 'Conversation not found'
            }), 404

        # Check if user is part of the conversation
        if conversation.user1_id != g.user.id and conversation.user2_id != g.user.id:
            return jsonify({
                'success': False,
                'error': 'You are not part of this conversation'
            }), 403

        # Get page parameter for pagination
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        # Get messages
        messages = Message.query.filter_by(conversation_id=conversation_id).order_by(
            Message.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)

        # Format messages
        formatted_messages = []
        for message in messages.items:
            formatted_messages.append({
                'id': message.id,
                'conversation_id': message.conversation_id,
                'sender_id': message.sender_id,
                'recipient_id': message.recipient_id,
                'content': message.content,
                'created_at': message.created_at.isoformat(),
                'read': message.read
            })

        # Mark unread messages as read
        unread_messages = Message.query.filter_by(
            conversation_id=conversation_id,
            recipient_id=g.user.id,
            read=False
        ).all()

        for message in unread_messages:
            message.read = True
        
        db.session.commit()

        return jsonify({
            'success': True,
            'messages': formatted_messages,
            'pagination': {
                'current_page': messages.page,
                'total_pages': messages.pages,
                'total_items': messages.total,
                'per_page': messages.per_page
            }
        })

    except Exception as e:
        logger.error(f"Error getting messages: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while getting messages'
        }), 500

@api_bp.route('/conversations', methods=['GET'])
def get_conversations():
    """Get all conversations for the current user"""
    try:
        if not g.user:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401

        # Get conversations
        conversations = Conversation.query.filter(
            (Conversation.user1_id == g.user.id) | (Conversation.user2_id == g.user.id)
        ).order_by(Conversation.last_message_at.desc()).all()

        # Format conversations
        formatted_conversations = []
        for conversation in conversations:
            # Get other user
            other_user_id = conversation.user2_id if conversation.user1_id == g.user.id else conversation.user1_id
            other_user = User.query.get(other_user_id)

            # Get last message
            last_message = Message.query.filter_by(conversation_id=conversation.id).order_by(
                Message.created_at.desc()
            ).first()

            # Get unread count
            unread_count = Message.query.filter_by(
                conversation_id=conversation.id,
                recipient_id=g.user.id,
                read=False
            ).count()

            formatted_conversations.append({
                'id': conversation.id,
                'other_user': {
                    'id': other_user.id,
                    'username': other_user.username,
                    'profile_pic': other_user.profile_pic
                },
                'last_message': {
                    'id': last_message.id,
                    'content': last_message.content,
                    'created_at': last_message.created_at.isoformat(),
                    'sender_id': last_message.sender_id,
                    'read': last_message.read
                } if last_message else None,
                'unread_count': unread_count,
                'last_message_at': conversation.last_message_at.isoformat() if conversation.last_message_at else None
            })

        return jsonify({
            'success': True,
            'conversations': formatted_conversations
        })

    except Exception as e:
        logger.error(f"Error getting conversations: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while getting conversations'
        }), 500
