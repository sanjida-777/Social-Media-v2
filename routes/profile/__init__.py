import logging
from flask import Blueprint

# Set up logger
logger = logging.getLogger(__name__)

# Create blueprint
profile_bp = Blueprint('profile', __name__, url_prefix='/profile')

# Note: Route modules will be imported in each module file
# to avoid circular imports
