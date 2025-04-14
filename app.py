import os
import logging
import uuid
from datetime import datetime

from flask import Flask, request, session, g
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_socketio import SocketIO
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename

# Set up logger
logger = logging.getLogger(__name__)

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

# Configure uploads
app.config["UPLOAD_FOLDER_PHOTOS"] = "static/uploads/photos"
app.config["UPLOAD_FOLDER_VIDEOS"] = "static/uploads/videos"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max upload
app.config["ALLOWED_PHOTO_EXTENSIONS"] = ["jpg", "jpeg", "png", "gif"]
app.config["ALLOWED_VIDEO_EXTENSIONS"] = ["mp4", "webm", "ogg"]

# Create upload directories if they don't exist
os.makedirs(app.config["UPLOAD_FOLDER_PHOTOS"], exist_ok=True)
os.makedirs(app.config["UPLOAD_FOLDER_VIDEOS"], exist_ok=True)

# Custom upload functions
def save_photo(file):
    if not allowed_photo(file.filename):
        return None
    
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    file_path = os.path.join(app.config["UPLOAD_FOLDER_PHOTOS"], unique_filename)
    file.save(file_path)
    return os.path.join("uploads/photos", unique_filename)

def save_video(file):
    if not allowed_video(file.filename):
        return None
    
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    file_path = os.path.join(app.config["UPLOAD_FOLDER_VIDEOS"], unique_filename)
    file.save(file_path)
    return os.path.join("uploads/videos", unique_filename)

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
