import os
import json
import logging
import requests
from functools import wraps
from firebase_admin import auth, initialize_app, credentials
import firebase_admin

# Set up logger
logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK with credentials from environment variable
def initialize_firebase():
    try:
        firebase_credentials_json = os.environ.get('FIREBASE_CREDENTIALS')
        
        if not firebase_credentials_json:
            logger.warning("Firebase credentials not found in environment variables, using dummy credentials for development")
            # Use dummy credentials for development
            cred = credentials.Certificate({
                "type": "service_account",
                "project_id": "fblike-app",
                "private_key_id": "dummy",
                "private_key": "-----BEGIN PRIVATE KEY-----\nDUMMY\n-----END PRIVATE KEY-----\n",
                "client_email": "dummy@fblike-app.iam.gserviceaccount.com",
                "client_id": "12345",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/dummy%40fblike-app.iam.gserviceaccount.com"
            })
        else:
            # Parse credentials from environment variable
            cred_dict = json.loads(firebase_credentials_json)
            cred = credentials.Certificate(cred_dict)
        
        # Initialize Firebase Admin with credentials
        initialize_app(cred)
        logger.info("Firebase Admin SDK initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing Firebase Admin SDK: {e}")
        raise

# Initialize Firebase Admin SDK
firebase_initialized = False
try:
    initialize_firebase()
    firebase_initialized = True
except Exception as e:
    logger.error(f"Firebase initialization failed: {e}")
    # Let the application continue without Firebase

def verify_firebase_token(token):
    """
    Verify Firebase ID token and return user info if valid
    """
    if not firebase_initialized:
        logger.warning("Firebase not initialized, cannot verify token")
        return None
        
    try:
        # Verify the token
        decoded_token = auth.verify_id_token(token)
        
        # Get user info
        uid = decoded_token.get('uid')
        user = auth.get_user(uid)
        
        # Return user data
        return {
            'uid': user.uid,
            'email': user.email,
            'name': user.display_name,
            'picture': user.photo_url,
            'email_verified': user.email_verified
        }
    except Exception as e:
        logger.error(f"Error verifying Firebase token: {e}")
        return None

def create_firebase_user(email, password, display_name=None):
    """
    Create a new user in Firebase Authentication
    """
    if not firebase_initialized:
        logger.warning("Firebase not initialized, cannot create user")
        # Return a mock user for development
        return {'uid': 'dev_' + email.replace('@', '_').replace('.', '_')}
        
    try:
        user = auth.create_user(
            email=email,
            password=password,
            display_name=display_name,
            email_verified=False
        )
        return user
    except Exception as e:
        logger.error(f"Error creating Firebase user: {e}")
        # Return None instead of raising to avoid breaking the app
        return None

def delete_firebase_user(uid):
    """
    Delete a user from Firebase Authentication
    """
    if not firebase_initialized:
        logger.warning("Firebase not initialized, cannot delete user")
        return True
        
    try:
        auth.delete_user(uid)
        return True
    except Exception as e:
        logger.error(f"Error deleting Firebase user: {e}")
        # Return False instead of raising to avoid breaking the app
        return False

def update_firebase_user(uid, **kwargs):
    """
    Update user properties in Firebase Authentication
    """
    if not firebase_initialized:
        logger.warning("Firebase not initialized, cannot update user")
        return True
        
    try:
        auth.update_user(uid, **kwargs)
        return True
    except Exception as e:
        logger.error(f"Error updating Firebase user: {e}")
        # Return False instead of raising to avoid breaking the app
        return False
