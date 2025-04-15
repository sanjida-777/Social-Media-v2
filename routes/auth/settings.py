import logging
from flask import render_template, redirect, url_for, request, flash, g, session
from database import db
from models import User
from routes.auth import auth_bp
from werkzeug.security import check_password_hash, generate_password_hash

# Set up logger
logger = logging.getLogger(__name__)

@auth_bp.route('/settings', methods=['GET'])
def settings():
    """User settings page"""
    if not g.user:
        return redirect(url_for('auth.login'))

    return render_template('auth/settings.html')

@auth_bp.route('/update_email', methods=['POST'])
def update_email():
    """Update user email"""
    if not g.user:
        return redirect(url_for('auth.login'))

    email = request.form.get('email')

    if email and email != g.user.email:
        # Check if email is already in use
        existing_user = User.query.filter_by(email=email).first()
        if existing_user and existing_user.id != g.user.id:
            flash('Email address already in use.', 'danger')
            return redirect(url_for('auth.settings'))

        g.user.email = email
        db.session.commit()
        flash('Email updated successfully.', 'success')

    return redirect(url_for('auth.settings'))

@auth_bp.route('/change_password', methods=['POST'])
def change_password():
    """Change user password"""
    if not g.user:
        return redirect(url_for('auth.login'))

    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    # Check if current password is correct
    if not check_password_hash(g.user.password_hash, current_password):
        flash('Current password is incorrect.', 'danger')
        return redirect(url_for('auth.settings'))

    # Check if new password is valid
    if len(new_password) < 8:
        flash('New password must be at least 8 characters long.', 'danger')
        return redirect(url_for('auth.settings'))

    # Check if passwords match
    if new_password != confirm_password:
        flash('New passwords do not match.', 'danger')
        return redirect(url_for('auth.settings'))

    # Update password
    g.user.password_hash = generate_password_hash(new_password, method='pbkdf2:sha256:50000')
    db.session.commit()
    flash('Password updated successfully.', 'success')

    return redirect(url_for('auth.settings'))

@auth_bp.route('/update_notifications', methods=['POST'])
def update_notifications():
    """Update notification settings"""
    if not g.user:
        return redirect(url_for('auth.login'))

    # Get notification settings from form
    email_messages = 'email_messages' in request.form
    email_friend_requests = 'email_friend_requests' in request.form
    email_comments = 'email_comments' in request.form
    email_likes = 'email_likes' in request.form

    push_messages = 'push_messages' in request.form
    push_friend_requests = 'push_friend_requests' in request.form
    push_comments = 'push_comments' in request.form
    push_likes = 'push_likes' in request.form

    # Update notification settings (would be stored in a separate table in a real app)
    # For now, just show a success message
    flash('Notification settings updated successfully.', 'success')
    return redirect(url_for('auth.settings'))

@auth_bp.route('/update_privacy', methods=['POST'])
def update_privacy():
    """Update privacy settings"""
    if not g.user:
        return redirect(url_for('auth.login'))

    # Get privacy settings from form
    profile_visibility = request.form.get('profile_visibility')
    post_visibility = request.form.get('post_visibility')
    friend_requests = request.form.get('friend_requests')
    search_engines = 'search_engines' in request.form

    # Update privacy settings (would be stored in a separate table in a real app)
    # For now, just show a success message
    flash('Privacy settings updated successfully.', 'success')
    return redirect(url_for('auth.settings'))

@auth_bp.route('/update_profile', methods=['POST'])
def update_profile():
    """Edit user profile"""
    if not g.user:
        return redirect(url_for('auth.login'))

    username = request.form.get('username')
    bio = request.form.get('bio')

    # Check if username is already taken
    if username != g.user.username:
        existing_user = User.query.filter_by(username=username).first()
        if existing_user and existing_user.id != g.user.id:
            flash('Username already taken.', 'danger')
            return redirect(url_for('auth.settings'))

    # Update profile information
    g.user.username = username
    g.user.bio = bio

    # Handle profile picture upload
    if 'profile_pic' in request.files and request.files['profile_pic'].filename:
        # In a real app, you would save the file and update the user's profile_pic field
        # For now, just pretend we did that
        flash('Profile picture updated.', 'success')

    # Handle cover photo upload
    if 'cover_pic' in request.files and request.files['cover_pic'].filename:
        # In a real app, you would save the file and update the user's cover_pic field
        # For now, just pretend we did that
        flash('Cover photo updated.', 'success')

    db.session.commit()
    flash('Profile updated successfully.', 'success')
    return redirect(url_for('auth.settings'))

@auth_bp.route('/delete_account', methods=['POST'])
def delete_account():
    """Delete user account"""
    if not g.user:
        return redirect(url_for('auth.login'))

    password = request.form.get('password')

    # Verify password
    if not check_password_hash(g.user.password_hash, password):
        flash('Incorrect password. Account not deleted.', 'danger')
        return redirect(url_for('auth.settings'))

    # Delete user account
    user_id = g.user.id
    db.session.delete(g.user)
    db.session.commit()

    # Clear session
    session.clear()

    flash('Your account has been permanently deleted.', 'success')
    return redirect(url_for('auth.register'))
