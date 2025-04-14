import os
import json
import logging
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

from app import app, db
from models import User
from utils.firebase import verify_firebase_token

# Set up logger
logger = logging.getLogger(__name__)

# Create Blueprint
auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if g.user:
        return redirect(url_for('feed.index'))
    
    if request.method == 'POST':
        if request.is_json:
            # Handle API login (Firebase token)
            data = request.get_json()
            token = data.get('token')
            
            if not token:
                return jsonify({'error': 'No token provided'}), 400
            
            try:
                firebase_user = verify_firebase_token(token)
                if firebase_user:
                    # Check if user exists in our database
                    user = User.query.filter_by(firebase_uid=firebase_user['uid']).first()
                    
                    if not user:
                        # Create user if it doesn't exist
                        user = User(
                            firebase_uid=firebase_user['uid'],
                            username=firebase_user.get('name', '').replace(' ', '_').lower() + str(hash(firebase_user['uid']))[-5:],
                            email=firebase_user['email'],
                            profile_pic=firebase_user.get('picture', '')
                        )
                        db.session.add(user)
                        db.session.commit()
                    
                    # Set session
                    session['user_id'] = user.id
                    
                    # Update last_online
                    user.last_online = db.func.now()
                    db.session.commit()
                    
                    return jsonify({
                        'success': True,
                        'user': user.serialize(),
                        'redirect': url_for('feed.index')
                    })
                else:
                    return jsonify({'error': 'Invalid token'}), 401
            except Exception as e:
                logger.error(f"Error during Firebase login: {e}")
                return jsonify({'error': 'Authentication error'}), 401
        else:
            # Handle form login (fallback method)
            email = request.form.get('email')
            password = request.form.get('password')
            
            if not email or not password:
                flash('Email and password are required', 'danger')
                return render_template('login.html')
            
            user = User.query.filter_by(email=email).first()
            
            if user and check_password_hash(user.password_hash, password):
                session['user_id'] = user.id
                
                # Update last_online
                user.last_online = db.func.now()
                db.session.commit()
                
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect(url_for('feed.index'))
            else:
                flash('Invalid email or password', 'danger')
    
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if g.user:
        return redirect(url_for('feed.index'))
    
    if request.method == 'POST':
        if request.is_json:
            # Handle API registration (Firebase token)
            data = request.get_json()
            token = data.get('token')
            
            if not token:
                return jsonify({'error': 'No token provided'}), 400
            
            try:
                firebase_user = verify_firebase_token(token)
                if firebase_user:
                    # Check if user already exists
                    existing_user = User.query.filter_by(firebase_uid=firebase_user['uid']).first()
                    if existing_user:
                        return jsonify({'error': 'User already exists'}), 409
                    
                    # Create new user
                    user = User(
                        firebase_uid=firebase_user['uid'],
                        username=firebase_user.get('name', '').replace(' ', '_').lower() + str(hash(firebase_user['uid']))[-5:],
                        email=firebase_user['email'],
                        profile_pic=firebase_user.get('picture', '')
                    )
                    db.session.add(user)
                    db.session.commit()
                    
                    # Set session
                    session['user_id'] = user.id
                    
                    return jsonify({
                        'success': True,
                        'user': user.serialize(),
                        'redirect': url_for('feed.index')
                    })
                else:
                    return jsonify({'error': 'Invalid token'}), 401
            except Exception as e:
                logger.error(f"Error during Firebase registration: {e}")
                return jsonify({'error': 'Registration error'}), 400
        else:
            # Handle form registration (fallback method)
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            
            if not username or not email or not password:
                flash('All fields are required', 'danger')
                return render_template('register.html')
            
            # Check if username or email already exists
            if User.query.filter_by(username=username).first():
                flash('Username already taken', 'danger')
                return render_template('register.html')
            
            if User.query.filter_by(email=email).first():
                flash('Email already registered', 'danger')
                return render_template('register.html')
            
            # Create user
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password)
            )
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
    
    return render_template('register.html')

@auth_bp.route('/logout')
def logout():
    if g.user:
        # Update last_online before logging out
        g.user.last_online = db.func.now()
        db.session.commit()
    
    session.pop('user_id', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/auth/check')
def check_auth():
    if g.user:
        return jsonify({
            'authenticated': True,
            'user': g.user.serialize()
        })
    else:
        return jsonify({
            'authenticated': False
        })

# Register the blueprint with the app
app.register_blueprint(auth_bp)
