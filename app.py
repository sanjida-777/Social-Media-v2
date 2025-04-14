import os
import logging
import uuid
import json
from datetime import datetime

from flask import Flask, request, session, g
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_socketio import SocketIO
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename

# Load configuration
from config import get_config, get_allowed_image_extensions, get_allowed_video_extensions, get_max_upload_size

# Set up logger
logger = logging.getLogger(__name__)
log_level = get_config('development.log_level', 'DEBUG')
if isinstance(log_level, str):
    numeric_level = getattr(logging, log_level.upper(), logging.DEBUG)
    logging.basicConfig(level=numeric_level)
else:
    logging.basicConfig(level=logging.DEBUG)

# Set up the Base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy with the Base class
db = SQLAlchemy(model_class=Base)

# Create the Flask app
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

# Import multi-upload functionality
from utils.multi_upload import save_multi_uploads, get_first_working_url

# Custom upload functions
def save_photo(file):
    """
    Save a photo to multiple hosting services and return a single URL
    Falls back to local storage if no external services work
    """
    from models import FileUpload, db
    
    # Validate file extension
    if not allowed_photo(file.filename):
        logger.warning(f"Rejected file with invalid extension: {file.filename}")
        return None
    
    # First try to upload to multiple services
    urls = save_multi_uploads(file)
    if urls:
        # Store in database
        upload = FileUpload(
            original_filename=secure_filename(file.filename),
            primary_url=urls[0],
            fallback_urls=json.dumps(urls[1:]) if len(urls) > 1 else None,
            media_type='image'
        )
        with app.app_context():
            db.session.add(upload)
            db.session.commit()
            logger.info(f"File uploaded to external services: {upload.id} - {upload.original_filename}")
        return urls[0]
    
    # Fall back to local storage if external uploads fail
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    file_path = os.path.join(app.config["UPLOAD_FOLDER_PHOTOS"], unique_filename)
    file.save(file_path)
    local_url = os.path.join("uploads/photos", unique_filename)
    
    # Still track in the database even for local files
    upload = FileUpload(
        original_filename=filename,
        primary_url=local_url,
        media_type='image'
    )
    with app.app_context():
        db.session.add(upload)
        db.session.commit()
        logger.info(f"File saved locally: {upload.id} - {unique_filename} (external uploads failed)")
    
    return local_url

def save_video(file):
    """
    Save a video to local storage for now
    Note: Most image hosting services don't accept videos in free tier
    """
    from models import FileUpload, db
    
    if not allowed_video(file.filename):
        logger.warning(f"Rejected video with invalid extension: {file.filename}")
        return None
    
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    file_path = os.path.join(app.config["UPLOAD_FOLDER_VIDEOS"], unique_filename)
    file.save(file_path)
    local_url = os.path.join("uploads/videos", unique_filename)
    
    # Track in the database
    upload = FileUpload(
        original_filename=filename,
        primary_url=local_url,
        media_type='video'
    )
    with app.app_context():
        db.session.add(upload)
        db.session.commit()
        logger.info(f"Video saved locally: {upload.id} - {unique_filename}")
    
    return local_url

def allowed_photo(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config["ALLOWED_PHOTO_EXTENSIONS"]

def allowed_video(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config["ALLOWED_VIDEO_EXTENSIONS"]

# Initialize SocketIO for real-time features
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize the app with the SQLAlchemy extension
db.init_app(app)

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

# Create all tables in a with app context
with app.app_context():
    # Import models to ensure tables are created
    import models
    db.create_all()
    logger.info("Database tables created successfully")
