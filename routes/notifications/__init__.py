import logging
from flask import Blueprint

# Set up logger
logger = logging.getLogger(__name__)

# Create blueprint
notifications_bp = Blueprint('notifications', __name__, url_prefix='/notifications')

# Note: Route modules will be imported in each module file
# to avoid circular imports
