import logging
from flask_session import Session

# Import the create_app function
from create_app import create_app

# Import shared SocketIO instance
from socket_instance import socketio

# Set up logger
logger = logging.getLogger(__name__)

# Create the Flask app
app = create_app()

# Initialize Flask-Session
Session(app)

# Initialize SocketIO with the app
socketio.init_app(app, cors_allowed_origins="*")

# Log that SocketIO has been initialized
logger.info("SocketIO initialized with app")

# Blueprints are registered in create_app.py
# Routes are organized in modular structure under routes/ directory

# Create all tables in a with app context
with app.app_context():
    # Import database and models to ensure tables are created
    from database import db
    import models

    try:
        # Ensure the database connection works
        db.engine.connect()

        # Create all tables
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
        logger.error(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
        # Continue execution even if database setup fails
        # This allows the app to start and show appropriate error messages

# Import socket.io event handlers
import events

# Run the application
if __name__ == '__main__':
    logger.info("Starting application")
    socketio.run(app, debug=True, port=5000)
