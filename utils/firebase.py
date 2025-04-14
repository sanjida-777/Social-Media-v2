import os
import json
import logging
from functools import wraps
from flask import request, g, redirect, url_for, session

# Set up logger
logger = logging.getLogger(__name__)

# Firebase Admin SDK
import firebase_admin
from firebase_admin import credentials, auth

# Global variables
firebase_app = None
firebase_config = None

def initialize_firebase():
    """
    Initialize Firebase Admin SDK with service account credentials
    """
    global firebase_app, firebase_config
    
    try:
        # First, try to load credentials from existing firebase_cred.json
        cred_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'firebase_cred.json')
        
        if os.path.exists(cred_path):
            logger.info(f"Loading Firebase credentials from {cred_path}")
            cred = credentials.Certificate(cred_path)
            
            # Also load the configuration for client-side use
            with open(cred_path, 'r') as f:
                firebase_cred_data = json.load(f)
                
                # Construct client config from service account
                # For a complete social media app, we need a proper Firebase config
                firebase_project_id = firebase_cred_data.get('project_id', '')
                
                # Extract project ID from the service account
                if firebase_project_id:
                    firebase_config = {
                        # Required for client-side auth
                        "apiKey": os.environ.get("FIREBASE_API_KEY", "AIzaSyCyOPPtgESjypcucodg6xD4mQCtpBQsqfc"),
                        "authDomain": f"{firebase_project_id}.firebaseapp.com",
                        "projectId": firebase_project_id,
                        "storageBucket": f"{firebase_project_id}.appspot.com",
                        "messagingSenderId": "240524622311",
                        "appId": os.environ.get("FIREBASE_APP_ID", "1:240524622311:web:24bd8b1c6cb4e3d26c57ea")
                    }
                else:
                    firebase_config = {}
        else:
            # If no file, check for environment variables
            logger.warning("Firebase credentials file not found, checking environment variables")
            if os.environ.get("FIREBASE_CREDENTIALS"):
                cred_json = json.loads(os.environ.get("FIREBASE_CREDENTIALS"))
                cred = credentials.Certificate(cred_json)
                
                # Also load the configuration for client-side
                firebase_project_id = cred_json.get('project_id', '')
                
                if firebase_project_id:
                    firebase_config = {
                        "apiKey": os.environ.get("FIREBASE_API_KEY", "AIzaSyCyOPPtgESjypcucodg6xD4mQCtpBQsqfc"),
                        "authDomain": f"{firebase_project_id}.firebaseapp.com",
                        "projectId": firebase_project_id,
                        "storageBucket": f"{firebase_project_id}.appspot.com",
                        "messagingSenderId": "240524622311",
                        "appId": os.environ.get("FIREBASE_APP_ID", "1:240524622311:web:24bd8b1c6cb4e3d26c57ea")
                    }
                else:
                    firebase_config = {}
            else:
                # If no credentials available, use dummy for development
                logger.warning("Firebase credentials not found in file or environment variables")
                return None
        
        # Initialize the app if we have valid credentials
        firebase_app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized successfully")
        return firebase_app
        
    except Exception as e:
        logger.error(f"Error initializing Firebase Admin SDK: {str(e)}")
        return None

# Initialize Firebase when this module is imported
firebase_app = initialize_firebase()

def get_firebase_config_for_client():
    """
    Get Firebase configuration for client-side use
    """
    return firebase_config

def verify_firebase_token(id_token):
    """
    Verify Firebase ID token and return the decoded token
    Returns None if token is invalid
    """
    if not firebase_app:
        logger.warning("Cannot verify token: Firebase Admin SDK not initialized")
        return None
    
    try:
        # Verify the ID token
        decoded_token = auth.verify_id_token(id_token)
        logger.info(f"Successfully verified token for user: {decoded_token.get('uid')}")
        return decoded_token
    except Exception as e:
        logger.error(f"Error verifying Firebase token: {str(e)}")
        return None

def firebase_login_required(f):
    """
    Decorator to require Firebase authentication for certain views
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is logged in through session
        if g.user:
            return f(*args, **kwargs)
        
        # Check for Firebase ID token in request
        id_token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            # Extract token from 'Bearer <token>' format
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                id_token = parts[1]
        
        if not id_token:
            # Token not found, redirect to login
            return redirect(url_for('auth.login'))
        
        # Verify token
        decoded_token = verify_firebase_token(id_token)
        if not decoded_token:
            # Invalid token, redirect to login
            return redirect(url_for('auth.login'))
        
        # Token is valid, check if user exists in database
        from models import User
        
        user = User.query.filter_by(firebase_uid=decoded_token['uid']).first()
        if not user:
            # User not found in database, redirect to register
            session['firebase_token'] = id_token  # Save token for registration
            return redirect(url_for('auth.register'))
        
        # Set user in session
        session['user_id'] = user.id
        g.user = user
        
        return f(*args, **kwargs)
    
    return decorated_function