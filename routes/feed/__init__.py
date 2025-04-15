import logging
from flask import Blueprint

# Set up logger
logger = logging.getLogger(__name__)

# Create blueprint
feed_bp = Blueprint('feed', __name__, url_prefix='/feed')

# Note: Route modules will be imported in each module file
# to avoid circular imports
