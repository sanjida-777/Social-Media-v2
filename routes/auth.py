import os
import json
import logging
from functools import wraps
from datetime import datetime, timedelta

from flask import (
    Blueprint, render_template, redirect, url_for, 
    request, flash, session, g, jsonify, abort
)
from werkzeug.security import generate_password_hash, check_password_hash

from app import db
from models import User
from utils.firebase import verify_firebase_token

# Set up logger
logger = logging.getLogger(__name__)

# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Login required decorator
def login_required(f):
    """
    Decorator to require login for certain views
    Redirects to login page if user is not authenticated
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    # If user is already logged in, redirect to home
    if g.user:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('login.html')

        # Find user by email
        user = User.query.filter_by(email=email).first()

        # Check if user exists and password is correct
        if not user or not check_password_hash(user.password_hash, password):
            flash('Invalid email or password.', 'danger')
            return render_template('login.html')

        # Set user session
        session['user_id'] = user.id

        # Update last online time
        user.last_online = datetime.utcnow()
        db.session.commit()

        # Redirect to home page or next URL
        next_url = request.args.get('next')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
        return redirect(url_for('main.index'))

    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page"""
    # If user is already logged in, redirect to home
    if g.user:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('register.html')

        # Check if user already exists
        existing_user = User.query.filter(
            (User.email == email) | (User.username == username)
        ).first()

        if existing_user:
            if existing_user.email == email:
                flash('Email address already in use.', 'danger')
            else:
                flash('Username already taken.', 'danger')
            return render_template('register.html')

        # Create new user
        user = User(
            email=email,
            username=username,
            password_hash=generate_password_hash(password),
            created_at=datetime.utcnow()
        )

        try:
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error registering user: {str(e)}")
            flash('An error occurred during registration. Please try again.', 'danger')

    return render_template('register.html')

@auth_bp.route('/logout')
def logout():
    """Log out a user"""
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Password reset request page"""
    # If user is already logged in, redirect to home
    if g.user:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email = request.form.get('email')
        if not email:
            flash('Please enter your email address.', 'danger')
            return render_template('forgot_password.html')

        # Check if user exists
        user = User.query.filter_by(email=email).first()
        if user:
            # In a real app, we would send a password reset email here
            # For now, just show a success message
            flash('If an account exists with that email, password reset instructions have been sent.', 'success')
            return redirect(url_for('auth.login'))
        else:
            # Don't reveal that the user doesn't exist for security reasons
            flash('If an account exists with that email, password reset instructions have been sent.', 'success')
            return redirect(url_for('auth.login'))

    return render_template('forgot_password.html')

@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    """API endpoint for local login"""
    data = request.json

    if not data or not data.get('email') or not data.get('password'):
        return jsonify({
            'success': False,
            'message': 'Missing email or password'
        }), 400

    email = data.get('email')
    password = data.get('password')

    # Find user by email
    user = User.query.filter_by(email=email).first()

    # Check if user exists and password is correct
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({
            'success': False,
            'message': 'Invalid email or password'
        }), 401

    # Set user session
    session['user_id'] = user.id

    return jsonify({
        'success': True,
        'user': {
            'id': user.id,
            'email': user.email,
            'username': user.username
        }
    })

@auth_bp.route('/api/register', methods=['POST'])
def api_register():
    """API endpoint for local registration"""
    data = request.json

    if not data or not data.get('email') or not data.get('password') or not data.get('username'):
        return jsonify({
            'success': False,
            'message': 'Missing required fields'
        }), 400

    email = data.get('email')
    password = data.get('password')
    username = data.get('username')

    # Check if user already exists
    existing_user = User.query.filter(
        (User.email == email) | (User.username == username)
    ).first()

    if existing_user:
        if existing_user.email == email:
            return jsonify({
                'success': False,
                'message': 'Email already in use'
            }), 400
        else:
            return jsonify({
                'success': False,
                'message': 'Username already taken'
            }), 400

    # Create new user
    user = User(
        email=email,
        username=username,
        password_hash=generate_password_hash(password),
        created_at=datetime.utcnow()
    )

    try:
        db.session.add(user)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'User registered successfully'
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error registering user: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Registration failed: " + str(e)
        }), 400

@auth_bp.route('/api/session', methods=['POST'])
def create_session():
    """Create session from Firebase token"""
    data = request.json

    if not data or not data.get('token'):
        return jsonify({
            'success': False,
            'message': 'Missing token'
        }), 400

    token = data.get('token')
    token_data = verify_firebase_token(token)

    if not token_data:
        return jsonify({
            'success': False,
            'message': 'Invalid token'
        }), 401

    firebase_uid = token_data.get('uid')
    email = token_data.get('email')

    # Find or create user
    user = User.query.filter_by(firebase_uid=firebase_uid).first()

    if not user:
        # User is signing in with Firebase for the first time
        # Check if email exists (for local accounts)
        email_user = User.query.filter_by(email=email).first()

        if email_user:
            # Link existing account with Firebase
            email_user.firebase_uid = firebase_uid
            db.session.commit()
            user = email_user
        else:
            # Create new user
            username = email.split('@')[0]
            base_username = username
            count = 1

            # Make sure username is unique
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{count}"
                count += 1

            user = User(
                firebase_uid=firebase_uid,
                email=email,
                username=username,
                created_at=datetime.utcnow()
            )
            db.session.add(user)
            db.session.commit()

    # Set user session
    session['user_id'] = user.id

    return jsonify({
        'success': True,
        'user': {
            'id': user.id,
            'email': user.email,
            'username': user.username
        }
    })

@auth_bp.route('/api/me')
def get_current_user():
    """Get current user data"""
    if not g.user:
        return jsonify({
            'authenticated': False
        })

    return jsonify({
        'authenticated': True,
        'id': g.user.id,
        'email': g.user.email,
        'username': g.user.username
    })

@auth_bp.route('/api/update-profile', methods=['POST'])
def update_profile():
    """Update user profile from Firebase registration"""
    data = request.json

    if not data or not data.get('uid') or not data.get('username'):
        return jsonify({
            'success': False,
            'message': 'Missing required fields'
        }), 400

    firebase_uid = data.get('uid')
    username = data.get('username')

    # Find user by Firebase UID
    user = User.query.filter_by(firebase_uid=firebase_uid).first()

    if not user:
        return jsonify({
            'success': False,
            'message': 'User not found'
        }), 404

    # Update username
    user.username = username
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Profile updated successfully'
    })