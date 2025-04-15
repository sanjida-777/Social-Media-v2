"""
Migration script to assign unique 10-digit UIDs to all existing users
"""
import sys
import os

# Add the parent directory to the path so we can import from the project
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db
from models import User
from utils.uid_generator import generate_unique_uid
from create_app import create_app

def assign_uids():
    """
    Assign UIDs to all users who don't have one
    """
    # Create app context
    app = create_app()
    
    with app.app_context():
        # Get all users without a UID
        users_without_uid = User.query.filter(User.uid.is_(None)).all()
        
        print(f"Found {len(users_without_uid)} users without a UID")
        
        count = 0
        for user in users_without_uid:
            user.uid = generate_unique_uid()
            count += 1
            print(f"Assigned UID {user.uid} to user {user.username} (ID: {user.id})")
        
        # Commit changes
        db.session.commit()
        
        print(f"Successfully assigned UIDs to {count} users")

if __name__ == "__main__":
    assign_uids()
