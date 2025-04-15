# This file is kept for backward compatibility
# It imports and re-exports the new API structure

# Import the blueprint from the new structure
from routes.api import api_bp

# Import all the modules to ensure routes are registered
import routes.api.profile
import routes.api.feed
import routes.api.stories
import routes.api.search
import routes.api.messages
