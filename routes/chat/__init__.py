import logging
from flask import Blueprint

# Set up logger
logger = logging.getLogger(__name__)

# Create blueprint
chat_bp = Blueprint('chat', __name__, url_prefix='/chat')

# Import route modules to register with blueprint
from routes.chat import messages, groups, realtime

# Note: The blueprint will be registered in create_app.py
