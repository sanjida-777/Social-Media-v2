"""
Script to recreate the database with the updated schema
"""
from database import db
from models import User
from create_app import create_app
from utils.uid_generator import generate_unique_uid
import os

def recreate_database():
    """
    Recreate the database with the updated schema
    """
    # Create app context
    app = create_app()
    
    with app.app_context():
        # Get the database path from the app config
        db_path = app.config.get('DATABASE_PATH', 'fblike.db')
        
        print(f"Using database at: {db_path}")
        
        # Delete the database file if it exists
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"Deleted existing database: {db_path}")
        
        # Create all tables
        db.create_all()
        print("Created all tables with the updated schema")
        
        # Create a test user with a UID
        test_user = User(
            uid=generate_unique_uid(),
            username="testuser",
            email="test@example.com",
            password_hash="pbkdf2:sha256:50000$TCI4GzcX$0de171a4f4dac32e3364c7ddc7c14f3e2fa61f2d17574483f7ffbb431b4acb2f",
            bio="This is a test user",
            profile_pic="/static/images/default-avatar.svg",
            cover_pic="/static/images/default-cover.svg"
        )
        
        db.session.add(test_user)
        db.session.commit()
        
        print(f"Created test user with UID: {test_user.uid}")

if __name__ == "__main__":
    recreate_database()
