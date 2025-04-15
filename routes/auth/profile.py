import logging
from flask import render_template, redirect, url_for, request, flash, g
from database import db
from models import User, Friend
from routes.auth import auth_bp

# Set up logger
logger = logging.getLogger(__name__)

@auth_bp.route('/profile', methods=['GET'])
@auth_bp.route('/profile/<username>', methods=['GET'])
def profile(username=None):
    """User profile page"""
    # Check if uid is provided as a query parameter
    uid = request.args.get('uid')

    if uid:
        # If uid is provided, find user by ID
        user = User.query.get_or_404(uid)
    elif username:
        # If username is provided in the URL, find user by username
        user = User.query.filter_by(username=username).first_or_404()
    else:
        # If neither uid nor username is provided, redirect to current user's profile
        if g.user:
            return redirect(url_for('auth.profile', username=g.user.username))
        else:
            return redirect(url_for('auth.login'))

    # Get user's posts
    posts = []

    # Get user's friends
    friends = []

    # Check if the current user is friends with this user
    is_friend = False

    # Check if the current user has sent a friend request to this user
    friend_request_sent = False

    # Check if this user has sent a friend request to the current user
    friend_request_received = False

    return render_template(
        'profile/profile.html',
        profile_user=user,
        posts=posts,
        friends=friends,
        is_friend=is_friend,
        friend_request_sent=friend_request_sent,
        friend_request_received=friend_request_received
    )

@auth_bp.route('/edit-profile', methods=['GET', 'POST'])
def edit_profile():
    """Edit user profile"""
    if not g.user:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        username = request.form.get('username')
        bio = request.form.get('bio')

        # Check if username is taken by another user
        existing_user = User.query.filter(User.username == username, User.id != g.user.id).first()
        if existing_user:
            flash('Username is already taken', 'error')
            return redirect(url_for('auth.edit_profile'))

        # Update user profile
        g.user.username = username
        g.user.bio = bio

        # Handle profile picture upload
        if 'profile_pic' in request.files and request.files['profile_pic'].filename:
            from utils.upload import save_photo
            profile_pic = save_photo(request.files['profile_pic'])
            if profile_pic:
                g.user.profile_pic = profile_pic

        # Handle cover picture upload
        if 'cover_pic' in request.files and request.files['cover_pic'].filename:
            from utils.upload import save_photo
            cover_pic = save_photo(request.files['cover_pic'])
            if cover_pic:
                g.user.cover_pic = cover_pic

        db.session.commit()
        flash('Profile updated successfully', 'success')
        return redirect(url_for('auth.profile', username=g.user.username))

    return render_template('profile/edit_profile.html')
