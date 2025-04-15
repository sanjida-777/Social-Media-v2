import logging
from flask import Blueprint

# Set up logger
logger = logging.getLogger(__name__)

# Create blueprint
story_bp = Blueprint('story', __name__, url_prefix='/story')

# Note: Route modules will be imported in each module file
# to avoid circular imports
