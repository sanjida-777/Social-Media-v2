import os
import logging
from datetime import datetime
from flask import Flask, request, session, g
from flask_socketio import SocketIO
from werkzeug.middleware.proxy_fix import ProxyFix

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
    app.secret_key = os.environ.get("SESSION_SECRET", "fb-like-app-secret-key")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

    # Configure the database
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///fblike.db")
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

    # Register blueprints
    from routes.auth import auth_bp
    from routes.feed import feed_bp
    from routes.main import main_bp
    from routes.story import story_bp
    from routes.notifications import notifications_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(feed_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(story_bp)
    app.register_blueprint(notifications_bp)

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
        g.request_time = datetime.utcnow()

        # Log request details
        logger.debug(f"Request: {request.method} {request.path} from {request.remote_addr}")

    @app.after_request
    def after_request(response):
        # Calculate request time
        if hasattr(g, 'request_time'):
            duration = datetime.utcnow() - g.request_time
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
