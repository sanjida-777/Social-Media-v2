import logging
from flask import render_template, redirect, url_for, request, flash, g, jsonify
from database import db
from models import User, Friend
from routes.auth import auth_bp

# Set up logger
logger = logging.getLogger(__name__)

@auth_bp.route('/friends')
def friends():
    """Friends and friend requests"""
    if not g.user:
        return redirect(url_for('auth.login'))

    # Get friends
    sent_friends = Friend.query.filter_by(user_id=g.user.id, status='accepted').all()
    received_friends = Friend.query.filter_by(friend_id=g.user.id, status='accepted').all()

    # Get friend IDs
    sent_friend_ids = [f.friend_id for f in sent_friends]
    received_friend_ids = [f.user_id for f in received_friends]

    # Combine IDs
    friend_ids = list(set(sent_friend_ids + received_friend_ids))

    # Get friend users
    friends = User.query.filter(User.id.in_(friend_ids)).all() if friend_ids else []

    # Get friend requests
    received_requests = Friend.query.filter_by(friend_id=g.user.id, status='pending').all()
    friend_requests = []

    for request in received_requests:
        sender = User.query.get(request.user_id)
        if sender:
            friend_requests.append({
                'id': request.id,
                'sender': sender,
                'created_at': request.created_at
            })

    # Get friend suggestions (users who are not friends and have no pending requests)
    # For simplicity, just get some random users
    all_users = User.query.filter(User.id != g.user.id).limit(10).all()
    friend_suggestions = []

    for user in all_users:
        # Check if already friends
        if user.id in friend_ids:
            continue

        # Check if friend request already sent
        sent_request = Friend.query.filter_by(
            user_id=g.user.id, friend_id=user.id, status='pending'
        ).first()
        if sent_request:
            continue

        # Check if friend request already received
        received_request = Friend.query.filter_by(
            user_id=user.id, friend_id=g.user.id, status='pending'
        ).first()
        if received_request:
            continue

        # Calculate mutual friends
        # Get user's friends
        user_sent_friends = Friend.query.filter_by(user_id=user.id, status='accepted').all()
        user_received_friends = Friend.query.filter_by(friend_id=user.id, status='accepted').all()

        # Get friend IDs
        user_sent_friend_ids = [f.friend_id for f in user_sent_friends]
        user_received_friend_ids = [f.user_id for f in user_received_friends]

        # Combine IDs
        user_friend_ids = list(set(user_sent_friend_ids + user_received_friend_ids))

        # Find mutual friends (intersection of current user's friends and this user's friends)
        mutual_friend_ids = list(set(friend_ids) & set(user_friend_ids))
        mutual_friends_count = len(mutual_friend_ids)

        # Add mutual friends count to user object
        user.mutual_friends = mutual_friends_count

        # Add to suggestions
        friend_suggestions.append(user)

    return render_template(
        'friends/friends.html',
        friends=friends,
        friend_requests=friend_requests,
        friend_suggestions=friend_suggestions
    )

@auth_bp.route('/api/friends/request', methods=['POST'])
def send_friend_request():
    """Send a friend request"""
    if not g.user:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    data = request.get_json()
    if not data or 'friend_id' not in data:
        return jsonify({'success': False, 'message': 'Missing friend_id'}), 400

    friend_id = data['friend_id']
    friend = User.query.get(friend_id)
    if not friend:
        return jsonify({'success': False, 'message': 'User not found'}), 404

    # Check if already friends
    existing_friendship = Friend.query.filter(
        ((Friend.user_id == g.user.id) & (Friend.friend_id == friend_id) & (Friend.status == 'accepted')) |
        ((Friend.user_id == friend_id) & (Friend.friend_id == g.user.id) & (Friend.status == 'accepted'))
    ).first()
    if existing_friendship:
        return jsonify({'success': False, 'message': 'Already friends'}), 400

    # Check if request already sent
    existing_request = Friend.query.filter_by(
        user_id=g.user.id, friend_id=friend_id, status='pending'
    ).first()
    if existing_request:
        return jsonify({'success': False, 'message': 'Friend request already sent'}), 400

    # Create friend request
    friend_request = Friend(
        user_id=g.user.id,
        friend_id=friend_id,
        status='pending'
    )
    db.session.add(friend_request)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Friend request sent'})

@auth_bp.route('/api/friends/accept', methods=['POST'])
def accept_friend_request():
    """Accept a friend request"""
    if not g.user:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    data = request.get_json()
    if not data or 'request_id' not in data:
        return jsonify({'success': False, 'message': 'Missing request_id'}), 400

    request_id = data['request_id']
    friend_request = Friend.query.get(request_id)
    if not friend_request:
        return jsonify({'success': False, 'message': 'Friend request not found'}), 404

    # Check if request is for current user
    if friend_request.friend_id != g.user.id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403

    # Accept request
    friend_request.status = 'accepted'
    db.session.commit()

    return jsonify({'success': True, 'message': 'Friend request accepted'})

@auth_bp.route('/api/friends/reject', methods=['POST'])
def reject_friend_request():
    """Reject a friend request"""
    if not g.user:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    data = request.get_json()
    if not data or 'request_id' not in data:
        return jsonify({'success': False, 'message': 'Missing request_id'}), 400

    request_id = data['request_id']
    friend_request = Friend.query.get(request_id)
    if not friend_request:
        return jsonify({'success': False, 'message': 'Friend request not found'}), 404

    # Check if request is for current user
    if friend_request.friend_id != g.user.id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403

    # Delete request
    db.session.delete(friend_request)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Friend request rejected'})

@auth_bp.route('/api/friends/unfriend', methods=['POST'])
def unfriend():
    """Remove a friend"""
    if not g.user:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    data = request.get_json()
    if not data or 'friend_id' not in data:
        return jsonify({'success': False, 'message': 'Missing friend_id'}), 400

    friend_id = data['friend_id']

    # Find friendship records
    friendship1 = Friend.query.filter_by(
        user_id=g.user.id, friend_id=friend_id, status='accepted'
    ).first()

    friendship2 = Friend.query.filter_by(
        user_id=friend_id, friend_id=g.user.id, status='accepted'
    ).first()

    if not friendship1 and not friendship2:
        return jsonify({'success': False, 'message': 'Not friends'}), 400

    # Delete friendship records
    if friendship1:
        db.session.delete(friendship1)

    if friendship2:
        db.session.delete(friendship2)

    db.session.commit()

    return jsonify({'success': True, 'message': 'Friend removed'})
