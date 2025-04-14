import sqlite3
import os

def update_user_table():
    """
    Update the user table to make firebase_uid nullable
    """
    # Connect to the database
    db_path = os.path.join('instance', 'fblike.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Create a new table with the correct schema
        cursor.execute('''
        CREATE TABLE user_new (
            id INTEGER PRIMARY KEY,
            firebase_uid VARCHAR(128) UNIQUE,
            username VARCHAR(64) NOT NULL UNIQUE,
            email VARCHAR(120) NOT NULL UNIQUE,
            password_hash VARCHAR(256),
            bio VARCHAR(500),
            profile_pic VARCHAR(200),
            cover_pic VARCHAR(200),
            created_at DATETIME,
            last_online DATETIME,
            is_active BOOLEAN,
            notification_settings VARCHAR(500)
        )
        ''')
        
        # Copy data from the old table to the new one
        cursor.execute('''
        INSERT INTO user_new 
        SELECT id, firebase_uid, username, email, password_hash, bio, profile_pic, cover_pic, 
               created_at, last_online, is_active, notification_settings
        FROM user
        ''')
        
        # Drop the old table
        cursor.execute('DROP TABLE user')
        
        # Rename the new table to the original name
        cursor.execute('ALTER TABLE user_new RENAME TO user')
        
        # Commit the changes
        conn.commit()
        print("Database schema updated successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"Error updating database schema: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    update_user_table()
