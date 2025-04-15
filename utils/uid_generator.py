import random
import string
from models import User
from database import db

def generate_uid(length=10):
    """
    Generate a random alphanumeric string of specified length
    """
    characters = string.digits  # Only digits for a numeric UID
    return ''.join(random.choice(characters) for _ in range(length))

def generate_unique_uid(length=10, max_attempts=100):
    """
    Generate a unique user ID that doesn't exist in the database
    
    Args:
        length (int): Length of the UID
        max_attempts (int): Maximum number of attempts to generate a unique UID
        
    Returns:
        str: A unique UID
        
    Raises:
        RuntimeError: If unable to generate a unique UID after max_attempts
    """
    for _ in range(max_attempts):
        # Generate a UID
        uid = generate_uid(length)
        
        # Ensure first digit is not 0 for a true 10-digit number
        if uid[0] == '0':
            uid = str(random.randint(1, 9)) + uid[1:]
            
        # Check if it exists in the database
        existing_user = User.query.filter_by(uid=uid).first()
        
        # If it doesn't exist, return it
        if not existing_user:
            return uid
    
    # If we've tried max_attempts times and still haven't found a unique UID
    raise RuntimeError(f"Unable to generate a unique UID after {max_attempts} attempts")

def assign_uids_to_existing_users():
    """
    Assign UIDs to existing users who don't have one
    
    Returns:
        int: Number of users updated
    """
    # Get all users without a UID
    users_without_uid = User.query.filter(User.uid.is_(None)).all()
    
    count = 0
    for user in users_without_uid:
        user.uid = generate_unique_uid()
        count += 1
    
    # Commit changes
    db.session.commit()
    
    return count
