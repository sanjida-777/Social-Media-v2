import logging
from datetime import datetime
from flask import render_template, redirect, url_for, request, flash, session, g, jsonify
from werkzeug.security import generate_password_hash
from sqlalchemy import func
from database import db
from models import User
from routes.auth import auth_bp

# Set up logger
logger = logging.getLogger(__name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page"""
    # If user is already logged in, redirect to home
    if g.user:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        # Get form data with CSRF protection
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Log registration attempt (without password)
        logger.info(f"Registration attempt for email: {email}, username: {username}")

        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('auth/register.html')

        # Validate password strength
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return render_template('auth/register.html')

        # Check if passwords match
        if confirm_password and password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html')

        # Check if user already exists
        existing_user = User.query.filter(
            (User.email == email) | (User.username == username)
        ).first()

        if existing_user:
            if existing_user.email == email:
                flash('Email address already in use.', 'danger')
            else:
                flash('Username already taken.', 'danger')
            return render_template('auth/register.html')

        # Import the UID generator
        from utils.uid_generator import generate_unique_uid

        # Create new user with secure password hashing
        new_user = User(
            uid=generate_unique_uid(),
            username=username,
            email=email,
            password_hash=generate_password_hash(password, method='pbkdf2:sha256:50000'),
            created_at=datetime.now(),
            last_online=datetime.now()
        )

        # Add user to database
        db.session.add(new_user)
        db.session.commit()

        # Log successful registration
        logger.info(f"User registered successfully: {new_user.id} - {new_user.email}")

        # Log user in with secure session
        session['user_id'] = new_user.id
        session.permanent = True  # Use permanent session

        flash('Registration successful!', 'success')
        return redirect(url_for('main.index'))

    return render_template('auth/register.html')

@auth_bp.route('/api/register', methods=['POST'])
def api_register():
    """API endpoint for registration"""
    # Get JSON data
    data = request.get_json()
    if not data:
        logger.debug("No JSON data received for registration")
        return jsonify({
            'success': False,
            'message': 'No data provided'
        }), 400

    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    # Log registration attempt (without password)
    logger.info(f"API registration attempt for email: {email}, username: {username}")

    if not username or not email or not password:
        return jsonify({
            'success': False,
            'message': 'All fields are required'
        }), 400

    # Validate password strength
    if len(password) < 8:
        return jsonify({
            'success': False,
            'message': 'Password must be at least 8 characters long'
        }), 400

    # Check if user already exists (case-insensitive email check)
    existing_user = User.query.filter(
        (func.lower(User.email) == func.lower(email)) | (User.username == username)
    ).first()

    if existing_user:
        if existing_user.email == email:
            logger.warning(f"API registration failed: email already in use: {email}")
            return jsonify({
                'success': False,
                'message': 'Email address already in use'
            }), 400
        else:
            logger.warning(f"API registration failed: username already taken: {username}")
            return jsonify({
                'success': False,
                'message': 'Username already taken'
            }), 400

    # Import the UID generator
    from utils.uid_generator import generate_unique_uid

    # Create new user with secure password hashing and unique UID
    new_user = User(
        uid=generate_unique_uid(),
        username=username,
        email=email,
        password_hash=generate_password_hash(password, method='pbkdf2:sha256:50000'),
        created_at=datetime.now(),
        last_online=datetime.now()
    )

    # Add user to database
    db.session.add(new_user)
    db.session.commit()

    # Log successful registration
    logger.info(f"API user registered successfully: {new_user.id} - {new_user.email}")

    # Log user in with secure session
    session['user_id'] = new_user.id
    session.permanent = True  # Use permanent session

    # Return user data (excluding sensitive information)
    return jsonify({
        'success': True,
        'user': {
            'id': new_user.id,
            'username': new_user.username,
            'email': new_user.email
        }
    })
