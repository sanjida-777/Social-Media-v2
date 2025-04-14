import os
import sys
import sqlite3
from datetime import datetime
import json

def test_registration():
    """
    Test user registration by directly inserting a user into the database
    """
    # Connect to the database
    db_path = os.path.join('instance', 'fblike.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Create a test user with firebase_uid set to None
        username = 'testuser'
        email = 'test@example.com'
        password_hash = 'test_hash'
        created_at = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        last_online = created_at
        notification_settings = json.dumps({
            'post_likes': True,
            'comments': True,
            'friend_requests': True,
            'messages': True,
            'story_views': True
        })
        
        # Check if user already exists
        cursor.execute('SELECT id FROM user WHERE username = ? OR email = ?', (username, email))
        existing_user = cursor.fetchone()
        
        if existing_user:
            print(f"User already exists with ID: {existing_user[0]}")
            return
        
        # Insert the user
        cursor.execute('''
        INSERT INTO user (
            firebase_uid, username, email, password_hash, bio, profile_pic, cover_pic,
            created_at, last_online, is_active, notification_settings
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            None,  # firebase_uid is None for local auth
            username,
            email,
            password_hash,
            None,  # bio
            '/static/images/default-avatar.svg',  # profile_pic
            '/static/images/default-cover.svg',  # cover_pic
            created_at,
            last_online,
            1,  # is_active
            notification_settings
        ))
        
        # Commit the changes
        conn.commit()
        print(f"Test user created successfully with ID: {cursor.lastrowid}")
        
    except Exception as e:
        conn.rollback()
        print(f"Error creating test user: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    test_registration()
