import os
import logging
from datetime import datetime, timedelta
from flask import Flask, request, session, g
from flask_socketio import SocketIO
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load configuration
from config import get_config, get_allowed_image_extensions, get_allowed_video_extensions, get_max_upload_size

# Import database
from database import db

# Set up logger
logger = logging.getLogger(__name__)
log_level = get_config('development.log_level', 'DEBUG')
if isinstance(log_level, str):
    numeric_level = getattr(logging, log_level.upper(), logging.DEBUG)
    logging.basicConfig(level=numeric_level)
else:
    logging.basicConfig(level=logging.DEBUG)

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)

    # Use secret key from .env file or fallback to a default (for development only)
    app.secret_key = os.getenv("SECRET_KEY", "fb-like-app-secret-key")

    # Configure session security
    app.config['SESSION_COOKIE_SECURE'] = os.getenv('ENVIRONMENT') != 'development'  # Secure in production
    app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # Session expiration

    # Configure proxy settings
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

    # Configure the database from .env
    # Use a direct path in the project root for SQLite database to avoid permission issues
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'fblike.db'))

    # Log the database path for debugging
    logger.info(f"Using database path: {db_path}")

    # Override the DATABASE_URL from .env with our direct path
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Configure uploads from config.json
    app.config["UPLOAD_FOLDER_PHOTOS"] = "static/uploads/photos"
    app.config["UPLOAD_FOLDER_VIDEOS"] = "static/uploads/videos"
    app.config["MAX_CONTENT_LENGTH"] = get_max_upload_size()
    app.config["ALLOWED_PHOTO_EXTENSIONS"] = get_allowed_image_extensions()
    app.config["ALLOWED_VIDEO_EXTENSIONS"] = get_allowed_video_extensions()

    # Create upload directories if they don't exist
    os.makedirs(app.config["UPLOAD_FOLDER_PHOTOS"], exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER_VIDEOS"], exist_ok=True)

    # Initialize the app with the SQLAlchemy extension
    db.init_app(app)

    # Register custom Jinja2 filters
    from utils.filters import register_filters
    register_filters(app)

    # Register blueprints
    from routes.auth import auth_bp
    from routes.feed import feed_bp
    from routes.main import main_bp
    from routes.story import story_bp
    from routes.notifications import notifications_bp
    from routes.api import api_bp  # Import the main API blueprint
    from routes.profile import profile_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(feed_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(story_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(api_bp)  # This registers all API routes
    app.register_blueprint(profile_bp)

    # Import Firebase utilities
    from utils.firebase import get_firebase_config_for_client

    # Create template context processor to inject Firebase config
    @app.context_processor
    def inject_firebase_config():
        """
        Add Firebase configuration to all templates
        This is more secure than hardcoding values in JavaScript files
        """
        return {
            'firebase_config': get_firebase_config_for_client()
        }

    @app.before_request
    def before_request():
        g.user = None
        if 'user_id' in session:
            from models import User
            g.user = User.query.get(session['user_id'])

        # Add current timestamp to g for logging and debugging
        g.request_time = datetime.now()

        # Log request details
        logger.debug(f"Request: {request.method} {request.path} from {request.remote_addr}")

    @app.after_request
    def after_request(response):
        # Calculate request time
        if hasattr(g, 'request_time'):
            duration = datetime.now() - g.request_time
            logger.debug(f"Request completed in {duration.total_seconds():.3f}s")
        return response

    return app

def allowed_photo(filename):
    """Check if a filename has an allowed photo extension"""
    from flask import current_app
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config["ALLOWED_PHOTO_EXTENSIONS"]

def allowed_video(filename):
    """Check if a filename has an allowed video extension"""
    from flask import current_app
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config["ALLOWED_VIDEO_EXTENSIONS"]
