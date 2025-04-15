from flask import Blueprint

# Create the main API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Import all API routes
from routes.api import profile, feed, stories, search, messages, user, friends

# Register all API routes with the blueprint
# Note: The imports above automatically register the routes with api_bp
