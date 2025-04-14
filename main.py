import os
import logging
from app import app, socketio

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Import routes
from routes import auth, feed, story, chat, profile, notifications

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
