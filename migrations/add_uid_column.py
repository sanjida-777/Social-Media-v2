"""
Migration script to add the uid column to the user table
"""
import sys
import os

# Add the parent directory to the path so we can import from the project
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db
from create_app import create_app
import sqlite3

def add_uid_column():
    """
    Add the uid column to the user table
    """
    # Create app context
    app = create_app()
    
    with app.app_context():
        # Get the database path from the app config
        db_path = app.config.get('DATABASE_PATH', 'fblike.db')
        
        print(f"Using database at: {db_path}")
        
        # Connect to the SQLite database directly
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # Check if the uid column already exists
            cursor.execute("PRAGMA table_info(user)")
            columns = cursor.fetchall()
            column_names = [column[1] for column in columns]
            
            if 'uid' not in column_names:
                print("Adding uid column to user table...")
                # Add the uid column (nullable initially)
                cursor.execute("ALTER TABLE user ADD COLUMN uid VARCHAR(10) UNIQUE")
                conn.commit()
                print("uid column added successfully")
            else:
                print("uid column already exists")
                
        except Exception as e:
            print(f"Error adding uid column: {e}")
            conn.rollback()
        finally:
            conn.close()

if __name__ == "__main__":
    add_uid_column()
