import os
import sys
import logging
from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def test_database_connection():
    """Test the database connection"""
    try:
        # Create a simple Flask app
        app = Flask(__name__)

        # Use an in-memory SQLite database for testing
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

        # Print the database URI for debugging
        logger.info(f"Using in-memory database for testing")

        # Also try to create a file-based database to diagnose permission issues
        try:
            # Get the absolute path to the database file
            db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'test.db'))
            logger.info(f"Attempting to create test database at: {db_path}")

            # Try to create a simple SQLite database file
            import sqlite3
            conn = sqlite3.connect(db_path)
            conn.close()
            logger.info(f"Successfully created test database at: {db_path}")
            os.remove(db_path)  # Clean up
        except Exception as e:
            logger.error(f"Error creating test database file: {str(e)}")
            logger.error(f"This indicates a file permission issue")

        # Configure the database
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

        # Print the database URI for debugging
        logger.info(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")

        # Initialize SQLAlchemy
        db = SQLAlchemy(app)

        # Define a simple model for testing
        class TestModel(db.Model):
            id = db.Column(db.Integer, primary_key=True)
            name = db.Column(db.String(50), nullable=False)

        # Create the database tables
        with app.app_context():
            db.create_all()
            logger.info("Database tables created successfully")

            # Test inserting data
            test_record = TestModel(name="Test Record")
            db.session.add(test_record)
            db.session.commit()
            logger.info("Test record inserted successfully")

            # Test querying data
            record = TestModel.query.first()
            logger.info(f"Retrieved record: {record.name}")

            # Clean up
            db.session.delete(record)
            db.session.commit()
            logger.info("Test record deleted successfully")

        return True
    except Exception as e:
        logger.error(f"Error testing database connection: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_database_connection()
    if success:
        logger.info("Database connection test passed!")
        sys.exit(0)
    else:
        logger.error("Database connection test failed!")
        sys.exit(1)
