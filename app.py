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

# Run the application
if __name__ == '__main__':
    logger.info("Starting application")
    app.run(debug=True, port=5000)
