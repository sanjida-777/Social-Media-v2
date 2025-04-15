"""
Script to assign UIDs to existing users
"""
import sqlite3
import random
import string
import os

def generate_uid(length=10):
    """
    Generate a random numeric string of specified length
    """
    characters = string.digits  # Only digits for a numeric UID
    uid = ''.join(random.choice(characters) for _ in range(length))
    
    # Ensure first digit is not 0 for a true 10-digit number
    if uid[0] == '0':
        uid = str(random.randint(1, 9)) + uid[1:]
    
    return uid

def is_uid_unique(cursor, uid):
    """
    Check if a UID is unique in the database
    """
    cursor.execute("SELECT COUNT(*) FROM user WHERE uid = ?", (uid,))
    count = cursor.fetchone()[0]
    return count == 0

def generate_unique_uid(cursor, length=10, max_attempts=100):
    """
    Generate a unique UID that doesn't exist in the database
    """
    for _ in range(max_attempts):
        uid = generate_uid(length)
        if is_uid_unique(cursor, uid):
            return uid
    
    raise RuntimeError(f"Unable to generate a unique UID after {max_attempts} attempts")

def assign_uids():
    """
    Assign UIDs to all users who don't have one
    """
    # Database path
    db_path = 'fblike.db'
    
    # Check if the database file exists
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return
    
    print(f"Using database at: {db_path}")
    
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get all users without a UID
        cursor.execute("SELECT id, username FROM user WHERE uid IS NULL")
        users_without_uid = cursor.fetchall()
        
        print(f"Found {len(users_without_uid)} users without a UID")
        
        count = 0
        for user_id, username in users_without_uid:
            uid = generate_unique_uid(cursor)
            cursor.execute("UPDATE user SET uid = ? WHERE id = ?", (uid, user_id))
            count += 1
            print(f"Assigned UID {uid} to user {username} (ID: {user_id})")
        
        # Commit changes
        conn.commit()
        
        print(f"Successfully assigned UIDs to {count} users")
        
    except Exception as e:
        print(f"Error assigning UIDs: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    assign_uids()
