import logging
from flask import Blueprint

# Set up logger
logger = logging.getLogger(__name__)

# Create blueprint
main_bp = Blueprint('main', __name__, url_prefix='')

# Note: Route modules will be imported in each module file
# to avoid circular imports
