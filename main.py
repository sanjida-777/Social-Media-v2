import os
import logging
from datetime import datetime
from app import app, socketio

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Import and register blueprints
from routes.main import main_bp
from routes.auth import auth_bp
from routes.chat import chat_bp

# Register blueprints
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(chat_bp)

# Add more routes when they're available
# from routes import feed, story, profile, notifications

# Add context processor for template variables
@app.context_processor
def utility_processor():
    return {
        'current_year': datetime.now().year
    }

# Add error handlers
@app.errorhandler(404)
def page_not_found(e):
    return "Page not found", 404

@app.errorhandler(500)
def internal_server_error(e):
    return "Internal server error", 500

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
