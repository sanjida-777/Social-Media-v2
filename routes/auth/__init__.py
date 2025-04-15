import logging
from flask import Blueprint

# Set up logger
logger = logging.getLogger(__name__)

# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Note: Route modules will be imported in each module file
# to avoid circular imports
