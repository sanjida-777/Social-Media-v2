import logging
from flask import Blueprint

# Set up logger
logger = logging.getLogger(__name__)

# Create blueprint
test_bp = Blueprint('test', __name__, url_prefix='/test')

# Note: Route modules will be imported in each module file
# to avoid circular imports
