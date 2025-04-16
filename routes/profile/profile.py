import os
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify
from werkzeug.security import generate_password_hash

from database import db
from models import User, Post, Friend, Follower, Notification, UserInteraction
from utils.upload import save_photo
from routes.auth import login_required

# Set up logger
logger = logging.getLogger(__name__)

# Create Blueprint
profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/profile', methods=['GET'])
@profile_bp.route('/profile/<username>', methods=['GET'])
def view_profile(username=None):
    # Check if uid is provided as a query parameter
    uid = request.args.get('uid')

    if uid:
        # If uid is provided, find user by UID (10-digit identifier)
        user = User.query.filter_by(uid=uid).first_or_404()
    elif username:
        # If username is provided in the URL, find user by username
        user = User.query.filter_by(username=username).first_or_404()
    else:
        # If neither uid nor username is provided, redirect to current user's profile
        if g.user:
            return redirect(url_for('profile.view_profile', username=g.user.username))
        else:
            return redirect(url_for('auth.login'))

    # If the viewer is logged in, record the profile visit
    if g.user and g.user.id != user.id:
        # Record interaction for relationship strength algorithm
        interaction = UserInteraction.query.filter_by(
            user_id=g.user.id,
            target_id=user.id,
            interaction_type='profile_visit'
        ).first()

        if interaction:
            interaction.interaction_count += 1
            interaction.last_interaction = db.func.now()
        else:
            interaction = UserInteraction(
                user_id=g.user.id,
                target_id=user.id,
                interaction_type='profile_visit'
            )
            db.session.add(interaction)

        db.session.commit()

    # Check friendship status
    friendship_status = None
    if g.user:
        # Check if the viewer has sent a friend request
        sent_request = Friend.query.filter_by(user_id=g.user.id, friend_id=user.id).first()
        if sent_request:
            friendship_status = sent_request.status

        # Check if the viewer has received a friend request
        if not friendship_status:
            received_request = Friend.query.filter_by(user_id=user.id, friend_id=g.user.id).first()
            if received_request:
                friendship_status = received_request.status

    # Get posts with pagination
    page = request.args.get('page', 1, type=int)
    per_page = 10

    posts = Post.query.filter_by(user_id=user.id).order_by(Post.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Get friend and follower counts
    friend_count = Friend.query.filter(
        (Friend.user_id == user.id) | (Friend.friend_id == user.id),
        Friend.status == 'accepted'
    ).count()

    follower_count = Follower.query.filter_by(user_id=user.id).count()
    following_count = Follower.query.filter_by(follower_id=user.id).count()

    # Check if the current user is following this user
    is_following = False
    if g.user:
        is_following = Follower.query.filter_by(follower_id=g.user.id, user_id=user.id).first() is not None

    # Get total posts count
    total_posts = Post.query.filter_by(user_id=user.id).count()

    # Check if this is an API request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('format') == 'json':
        # Return JSON response for API requests
        return jsonify({
            'user': user.serialize(),
            'friendship_status': friendship_status,
            'is_following': is_following,
            'friend_count': friend_count,
            'follower_count': follower_count,
            'following_count': following_count,
            'posts': [post.item.serialize() for post in posts.items],
            'pagination': {
                'current_page': page,
                'per_page': per_page,
                'total_posts': total_posts,
                'total_pages': (total_posts + per_page - 1) // per_page
            }
        })
    else:
        # Render HTML template for regular requests
        return render_template(
            'profile.html',
            profile_user=user,
            posts=posts,
            friends=[],  # We'll load these via AJAX
            is_friend=(friendship_status == 'accepted'),
            friend_request_sent=(friendship_status == 'pending'),
            friend_request_received=(friendship_status == 'received')
        )

@profile_bp.route('/api/profile/<username>')
def get_profile(username):
    user = User.query.filter_by(username=username).first_or_404()

    # Get posts with pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    posts_query = Post.query.filter_by(user_id=user.id).order_by(Post.created_at.desc())
    total_posts = posts_query.count()

    posts = posts_query.offset((page - 1) * per_page).limit(per_page).all()

    # Check friendship status
    friendship_status = None
    is_following = False
    if g.user:
        # Check if the viewer has sent a friend request
        sent_request = Friend.query.filter_by(user_id=g.user.id, friend_id=user.id).first()
        if sent_request:
            friendship_status = sent_request.status

        # Check if the viewer has received a friend request
        if not friendship_status:
            received_request = Friend.query.filter_by(user_id=user.id, friend_id=g.user.id).first()
            if received_request:
                friendship_status = received_request.status

        # Check if following
        is_following = Follower.query.filter_by(follower_id=g.user.id, user_id=user.id).first() is not None

    # Get friend and follower counts
    friend_count = Friend.query.filter(
        (Friend.user_id == user.id) | (Friend.friend_id == user.id),
        Friend.status == 'accepted'
    ).count()

    follower_count = Follower.query.filter_by(user_id=user.id).count()
    following_count = Follower.query.filter_by(follower_id=user.id).count()

    # Check if this is an API request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('format') == 'json':
        # Return JSON response for API requests
        return jsonify({
            'user': user.serialize(),
            'friendship_status': friendship_status,
            'is_following': is_following,
            'friend_count': friend_count,
            'follower_count': follower_count,
            'following_count': following_count,
            'posts': [post.serialize() for post in posts],
            'pagination': {
                'current_page': page,
                'per_page': per_page,
                'total_posts': total_posts,
                'total_pages': (total_posts + per_page - 1) // per_page
            }
        })
    else:
        # Render HTML template for regular requests
        return render_template(
            'profile.html',
            profile_user=user,
            posts=posts,
            friends=[],  # We'll load these via AJAX
            is_friend=(friendship_status == 'accepted'),
            friend_request_sent=(friendship_status == 'pending'),
            friend_request_received=(friendship_status == 'received')
        )

@profile_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        if request.is_json:
            # Handle API profile update
            data = request.get_json()

            username = data.get('username', '').strip()
            bio = data.get('bio', '').strip()
            email = data.get('email', '').strip()

            # Validate username
            if username and username != g.user.username:
                if User.query.filter_by(username=username).first():
                    return jsonify({'error': 'Username already taken'}), 400
                g.user.username = username

            # Update other fields
            if bio is not None:
                g.user.bio = bio

            if email and email != g.user.email:
                if User.query.filter_by(email=email).first():
                    return jsonify({'error': 'Email already registered'}), 400
                g.user.email = email

            db.session.commit()

            return jsonify({
                'success': True,
                'user': g.user.serialize()
            })
        else:
            # Handle form profile update
            username = request.form.get('username', '').strip()
            bio = request.form.get('bio', '').strip()
            email = request.form.get('email', '').strip()

            # Validate username
            if username and username != g.user.username:
                if User.query.filter_by(username=username).first():
                    flash('Username already taken', 'danger')
                    return redirect(url_for('profile.edit_profile'))
                g.user.username = username

            # Update other fields
            if bio is not None:
                g.user.bio = bio

            if email and email != g.user.email:
                if User.query.filter_by(email=email).first():
                    flash('Email already registered', 'danger')
                    return redirect(url_for('profile.edit_profile'))
                g.user.email = email

            # Handle profile picture
            if 'profile_pic' in request.files and request.files['profile_pic'].filename:
                profile_pic = request.files['profile_pic']
                media_path = save_photo(profile_pic)
                if not media_path:
                    flash('Invalid file type', 'danger')
                    return redirect(url_for('profile.edit_profile'))
                g.user.profile_pic = url_for('static', filename=media_path)

            # Handle cover picture
            if 'cover_pic' in request.files and request.files['cover_pic'].filename:
                cover_pic = request.files['cover_pic']
                media_path = save_photo(cover_pic)
                if not media_path:
                    flash('Invalid file type', 'danger')
                    return redirect(url_for('profile.edit_profile'))
                g.user.cover_pic = url_for('static', filename=media_path)

            db.session.commit()

            flash('Profile updated successfully', 'success')
            return redirect(url_for('profile.view_profile', username=g.user.username))

    return render_template('settings.html', user=g.user)

@profile_bp.route('/api/profile/upload_profile_pic', methods=['POST'])
@login_required
def upload_profile_pic():
    if 'profile_pic' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    profile_pic = request.files['profile_pic']

    if profile_pic.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    media_path = save_photo(profile_pic)
    if not media_path:
        return jsonify({'error': 'Invalid file type'}), 400
    g.user.profile_pic = url_for('static', filename=media_path)

    db.session.commit()

    return jsonify({
        'success': True,
        'profile_pic': g.user.profile_pic
    })

@profile_bp.route('/api/profile/upload_cover_pic', methods=['POST'])
@login_required
def upload_cover_pic():
    if 'cover_pic' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    cover_pic = request.files['cover_pic']

    if cover_pic.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    media_path = save_photo(cover_pic)
    if not media_path:
        return jsonify({'error': 'Invalid file type'}), 400
    g.user.cover_pic = url_for('static', filename=media_path)

    db.session.commit()

    return jsonify({
        'success': True,
        'cover_pic': g.user.cover_pic
    })

@profile_bp.route('/friends')
@login_required
def friends():
    return render_template('friends.html')

@profile_bp.route('/api/friends')
@login_required
def get_friends():
    # Get all accepted friendships
    sent_friends = Friend.query.filter_by(user_id=g.user.id, status='accepted').all()
    received_friends = Friend.query.filter_by(friend_id=g.user.id, status='accepted').all()

    # Get friend IDs
    sent_friend_ids = [f.friend_id for f in sent_friends]
    received_friend_ids = [f.user_id for f in received_friends]

    # Combine IDs
    friend_ids = list(set(sent_friend_ids + received_friend_ids))

    # Get friend users
    friends = User.query.filter(User.id.in_(friend_ids)).all()

    # Serialize friends with relationship scores
    friend_data = []
    for friend in friends:
        # Get the friendship record
        friendship = Friend.query.filter(
            ((Friend.user_id == g.user.id) & (Friend.friend_id == friend.id)) |
            ((Friend.user_id == friend.id) & (Friend.friend_id == g.user.id))
        ).first()

        friend_data.append({
            'user': friend.serialize(),
            'relationship_score': friendship.relationship_score if friendship else 0
        })

    # Sort by relationship score (highest first)
    friend_data.sort(key=lambda x: x['relationship_score'], reverse=True)

    return jsonify({
        'friends': friend_data,
        'count': len(friend_data)
    })

@profile_bp.route('/api/friend_requests')
@login_required
def get_friend_requests():
    # Get all pending friend requests
    received_requests = Friend.query.filter_by(friend_id=g.user.id, status='pending').all()

    # Get requestor IDs
    requestor_ids = [r.user_id for r in received_requests]

    # Get requestor users
    requestors = User.query.filter(User.id.in_(requestor_ids)).all()

    # Serialize requestors
    requestor_data = []
    for requestor in requestors:
        request_record = next((r for r in received_requests if r.user_id == requestor.id), None)

        requestor_data.append({
            'user': requestor.serialize(),
            'request_id': request_record.id if request_record else None,
            'created_at': request_record.created_at.isoformat() if request_record else None
        })

    return jsonify({
        'friend_requests': requestor_data,
        'count': len(requestor_data)
    })

@profile_bp.route('/api/friend_request/<username>', methods=['POST'])
@login_required
def send_friend_request(username):
    user = User.query.filter_by(username=username).first_or_404()

    # Can't friend yourself
    if user.id == g.user.id:
        return jsonify({'error': 'You cannot send a friend request to yourself'}), 400

    # Check if already friends or pending request
    existing_sent = Friend.query.filter_by(user_id=g.user.id, friend_id=user.id).first()
    existing_received = Friend.query.filter_by(user_id=user.id, friend_id=g.user.id).first()

    if existing_sent:
        return jsonify({'error': f'You already have a {existing_sent.status} friend request with this user'}), 400

    if existing_received:
        # If they sent us a request, accept it
        if existing_received.status == 'pending':
            existing_received.status = 'accepted'
            db.session.commit()

            # Create notification for the other user
            from models import Notification
            notification = Notification(
                user_id=user.id,
                notification_type='friend_accepted',
                sender_id=g.user.id,
                reference_id=None,
                content=f"{g.user.username} accepted your friend request"
            )
            db.session.add(notification)
            db.session.commit()

            return jsonify({
                'success': True,
                'status': 'accepted',
                'message': 'Friend request accepted'
            })
        else:
            return jsonify({'error': f'You already have a {existing_received.status} friend request with this user'}), 400

    # Check friend limit (1000)
    friend_count = Friend.query.filter(
        ((Friend.user_id == g.user.id) | (Friend.friend_id == g.user.id)),
        Friend.status == 'accepted'
    ).count()

    if friend_count >= 1000:
        return jsonify({'error': 'You have reached the maximum friend limit (1000)'}), 400

    # Create friend request
    friend_request = Friend(
        user_id=g.user.id,
        friend_id=user.id,
        status='pending'
    )
    db.session.add(friend_request)

    # Create notification for the other user
    from models import Notification
    notification = Notification(
        user_id=user.id,
        notification_type='friend_request',
        sender_id=g.user.id,
        reference_id=friend_request.id,
        content=f"{g.user.username} sent you a friend request"
    )
    db.session.add(notification)

    db.session.commit()

    return jsonify({
        'success': True,
        'status': 'pending',
        'message': 'Friend request sent'
    })

@profile_bp.route('/api/friend_request/<int:request_id>/accept', methods=['POST'])
@login_required
def accept_friend_request(request_id):
    friend_request = Friend.query.get_or_404(request_id)

    # Check if the request is to the current user
    if friend_request.friend_id != g.user.id:
        return jsonify({'error': 'This friend request is not for you'}), 403

    # Check if already accepted
    if friend_request.status != 'pending':
        return jsonify({'error': f'This friend request is already {friend_request.status}'}), 400

    # Accept the request
    friend_request.status = 'accepted'
    db.session.commit()

    # Create notification for the other user
    from models import Notification
    notification = Notification(
        user_id=friend_request.user_id,
        notification_type='friend_accepted',
        sender_id=g.user.id,
        reference_id=None,
        content=f"{g.user.username} accepted your friend request"
    )
    db.session.add(notification)
    db.session.commit()

    return jsonify({
        'success': True,
        'status': 'accepted',
        'message': 'Friend request accepted'
    })

@profile_bp.route('/api/friend_request/<int:request_id>/decline', methods=['POST'])
@login_required
def decline_friend_request(request_id):
    friend_request = Friend.query.get_or_404(request_id)

    # Check if the request is to the current user
    if friend_request.friend_id != g.user.id:
        return jsonify({'error': 'This friend request is not for you'}), 403

    # Check if already declined or accepted
    if friend_request.status != 'pending':
        return jsonify({'error': f'This friend request is already {friend_request.status}'}), 400

    # Decline the request
    friend_request.status = 'declined'
    db.session.commit()

    return jsonify({
        'success': True,
        'status': 'declined',
        'message': 'Friend request declined'
    })

@profile_bp.route('/api/friend_request/<username>/cancel', methods=['POST'])
@login_required
def cancel_friend_request(username):
    user = User.query.filter_by(username=username).first_or_404()

    # Find the friend request
    friend_request = Friend.query.filter_by(user_id=g.user.id, friend_id=user.id, status='pending').first()

    if not friend_request:
        return jsonify({'error': 'No pending friend request found'}), 404

    # Delete the friend request
    db.session.delete(friend_request)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Friend request cancelled'
    })

@profile_bp.route('/api/friend_request/<username>/accept', methods=['POST'])
@login_required
def accept_friend_request_by_username(username):
    user = User.query.filter_by(username=username).first_or_404()

    # Find the friend request
    friend_request = Friend.query.filter_by(user_id=user.id, friend_id=g.user.id, status='pending').first()

    if not friend_request:
        return jsonify({'error': 'No pending friend request found'}), 404

    # Accept the request
    friend_request.status = 'accepted'
    db.session.commit()

    # Create notification for the other user
    notification = Notification(
        user_id=user.id,
        notification_type='friend_accepted',
        sender_id=g.user.id,
        reference_id=None,
        content=f"{g.user.username} accepted your friend request"
    )
    db.session.add(notification)
    db.session.commit()

    return jsonify({
        'success': True,
        'status': 'accepted',
        'message': 'Friend request accepted'
    })

@profile_bp.route('/api/friend_request/<username>/decline', methods=['POST'])
@login_required
def decline_friend_request_by_username(username):
    user = User.query.filter_by(username=username).first_or_404()

    # Find the friend request
    friend_request = Friend.query.filter_by(user_id=user.id, friend_id=g.user.id, status='pending').first()

    if not friend_request:
        return jsonify({'error': 'No pending friend request found'}), 404

    # Decline the request
    friend_request.status = 'declined'
    db.session.commit()

    return jsonify({
        'success': True,
        'status': 'declined',
        'message': 'Friend request declined'
    })

@profile_bp.route('/api/friend/<username>/remove', methods=['POST'])
@login_required
def remove_friend(username):
    user = User.query.filter_by(username=username).first_or_404()

    # Check if they are friends
    friendship = Friend.query.filter(
        ((Friend.user_id == g.user.id) & (Friend.friend_id == user.id)) |
        ((Friend.user_id == user.id) & (Friend.friend_id == g.user.id))
    ).first()

    if not friendship or friendship.status != 'accepted':
        return jsonify({'error': 'You are not friends with this user'}), 400

    # Remove the friendship
    db.session.delete(friendship)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Friend removed'
    })

@profile_bp.route('/api/follow/<username>', methods=['POST'])
@login_required
def follow_user(username):
    user = User.query.filter_by(username=username).first_or_404()

    # Can't follow yourself
    if user.id == g.user.id:
        return jsonify({'error': 'You cannot follow yourself'}), 400

    # Check if already following
    existing_follow = Follower.query.filter_by(follower_id=g.user.id, user_id=user.id).first()

    if existing_follow:
        return jsonify({'error': 'You are already following this user'}), 400

    # Create follow
    follow = Follower(
        follower_id=g.user.id,
        user_id=user.id
    )
    db.session.add(follow)

    # Create notification for the other user
    from models import Notification
    notification = Notification(
        user_id=user.id,
        notification_type='follow',
        sender_id=g.user.id,
        reference_id=None,
        content=f"{g.user.username} started following you"
    )
    db.session.add(notification)

    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Following user'
    })

@profile_bp.route('/api/unfollow/<username>', methods=['POST'])
@login_required
def unfollow_user(username):
    user = User.query.filter_by(username=username).first_or_404()

    # Check if following
    follow = Follower.query.filter_by(follower_id=g.user.id, user_id=user.id).first()

    if not follow:
        return jsonify({'error': 'You are not following this user'}), 400

    # Remove follow
    db.session.delete(follow)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Unfollowed user'
    })

@profile_bp.route('/api/user/<int:user_id>', methods=['GET'])
def get_user_by_id(user_id):
    """Get user information by ID"""
    user = User.query.get(user_id)

    if not user:
        return jsonify({
            'success': False,
            'error': 'User not found'
        }), 404

    return jsonify({
        'success': True,
        'user': user.serialize()
    })

# Blueprint is registered in create_app.py
