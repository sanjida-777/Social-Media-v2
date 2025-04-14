import os
import logging
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify
from sqlalchemy import desc

from app import app, db, socketio
from models import User, Notification
from routes.auth import login_required

# Set up logger
logger = logging.getLogger(__name__)

# Create Blueprint
notifications_bp = Blueprint('notifications', __name__)

@notifications_bp.route('/notifications')
@login_required
def notifications():
    return render_template('notifications.html')

@notifications_bp.route('/api/notifications')
@login_required
def get_notifications():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Get notifications for the user with pagination
    notifications = Notification.query.filter_by(user_id=g.user.id).order_by(desc(Notification.created_at))
    total_notifications = notifications.count()
    
    notifications = notifications.offset((page - 1) * per_page).limit(per_page).all()
    
    # Serialize notifications
    serialized_notifications = [notification.serialize() for notification in notifications]
    
    # Get unread count
    unread_count = Notification.query.filter_by(user_id=g.user.id, is_read=False).count()
    
    return jsonify({
        'notifications': serialized_notifications,
        'unread_count': unread_count,
        'pagination': {
            'current_page': page,
            'per_page': per_page,
            'total_notifications': total_notifications,
            'total_pages': (total_notifications + per_page - 1) // per_page
        }
    })

@notifications_bp.route('/api/notifications/mark_read', methods=['POST'])
@login_required
def mark_notifications_read():
    if request.is_json:
        data = request.get_json()
        notification_ids = data.get('notification_ids', [])
        
        if notification_ids:
            # Mark specific notifications as read
            notifications = Notification.query.filter(
                Notification.id.in_(notification_ids),
                Notification.user_id == g.user.id
            ).all()
            
            for notification in notifications:
                notification.is_read = True
        else:
            # Mark all notifications as read
            Notification.query.filter_by(user_id=g.user.id, is_read=False).update({'is_read': True})
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'unread_count': Notification.query.filter_by(user_id=g.user.id, is_read=False).count()
        })
    else:
        return jsonify({'error': 'Request must be JSON'}), 400

@notifications_bp.route('/api/notifications/unread_count')
@login_required
def get_unread_count():
    unread_count = Notification.query.filter_by(user_id=g.user.id, is_read=False).count()
    
    return jsonify({
        'unread_count': unread_count
    })

# Socket.IO event handler for sending notifications in real-time
@socketio.on('get_notifications')
def handle_get_notifications():
    if not g.user:
        return {'error': 'You must be logged in'}
    
    # Get recent unread notifications
    recent_notifications = Notification.query.filter_by(
        user_id=g.user.id,
        is_read=False
    ).order_by(desc(Notification.created_at)).limit(5).all()
    
    # Get total unread count
    unread_count = Notification.query.filter_by(user_id=g.user.id, is_read=False).count()
    
    return {
        'success': True,
        'notifications': [notification.serialize() for notification in recent_notifications],
        'unread_count': unread_count
    }

# Function to emit a notification to a user (used by other routes)
def send_notification(user_id, notification_type, sender_id, reference_id, content):
    # Create notification
    notification = Notification(
        user_id=user_id,
        notification_type=notification_type,
        sender_id=sender_id,
        reference_id=reference_id,
        content=content
    )
    db.session.add(notification)
    db.session.commit()
    
    # Emit to user's notification room
    socketio.emit('new_notification', notification.serialize(), room=f'user_{user_id}')
    
    return notification

# Register the blueprint with the app
app.register_blueprint(notifications_bp)
