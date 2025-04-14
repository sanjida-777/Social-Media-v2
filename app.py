import logging
from flask_socketio import SocketIO

# Import the create_app function
from create_app import create_app

# Set up logger
logger = logging.getLogger(__name__)

# Create the Flask app
app = create_app()

# Initialize SocketIO for real-time features
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Blueprints are registered in create_app.py

# Create all tables in a with app context
with app.app_context():
    # Import database and models to ensure tables are created
    from database import db
    import models
    db.create_all()
    logger.info("Database tables created successfully")

# Run the application
if __name__ == '__main__':
    logger.info("Starting application")
    app.run(debug=True, port=5000)
