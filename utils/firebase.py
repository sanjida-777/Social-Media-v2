import os
import json
import logging
from functools import wraps
from flask import request, g, redirect, url_for, session
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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

        # Load Firebase configuration from environment variables
        firebase_config = {
            "apiKey": os.getenv("FIREBASE_API_KEY"),
            "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
            "projectId": os.getenv("FIREBASE_PROJECT_ID"),
            "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
            "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
            "appId": os.getenv("FIREBASE_APP_ID")
        }

        if os.path.exists(cred_path):
            logger.info(f"Loading Firebase credentials from {cred_path}")
            cred = credentials.Certificate(cred_path)

            # Initialize Firebase Admin SDK
            if not firebase_admin._apps:
                firebase_app = firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully")
            else:
                firebase_app = firebase_admin.get_app()
                logger.info("Using existing Firebase Admin SDK app")

            return firebase_app
        else:
            # If no file, check for environment variables
            logger.warning("Firebase credentials file not found, checking environment variables")

            # Check if we have the minimum required configuration
            if firebase_config["apiKey"] and firebase_config["projectId"]:
                try:
                    # Try to initialize with default credentials or environment variables
                    if not firebase_admin._apps:
                        # For development purposes, we can use a mock credential
                        mock_cred = {
                            "type": "service_account",
                            "project_id": firebase_config["projectId"],
                            "private_key_id": "mock-key-id",
                            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7VJTUt9Us8cKj\nMzEfYyjiWA4R4/M2bS1GB4t7NXp98C3SC6dVMvDuictGeurT8jNbvJZHtCSuYEvu\nNMoSfm76oqFvAp8Gy0iz5sxjZmSnXyCdPEovGhLa0VzMaQ8s+CLOyS56YyCFGeJZ\n-----END PRIVATE KEY-----\n",
                            "client_email": f"firebase-adminsdk@{firebase_config['projectId']}.iam.gserviceaccount.com",
                            "client_id": "mock-client-id",
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token",
                            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                            "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk%40{firebase_config['projectId']}.iam.gserviceaccount.com"
                        }
                        cred = credentials.Certificate(mock_cred)
                        firebase_app = firebase_admin.initialize_app(cred)
                        logger.info("Firebase Admin SDK initialized with mock credentials for development")
                    else:
                        firebase_app = firebase_admin.get_app()
                        logger.info("Using existing Firebase Admin SDK app")

                    return firebase_app
                except Exception as e:
                    logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
                    return None
            else:
                # Missing required configuration
                logger.warning("Missing required Firebase configuration in environment variables")
                return None

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