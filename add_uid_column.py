"""
Script to add the uid column to the user table using raw SQL
"""
import sqlite3
import os

def add_uid_column():
    """
    Add the uid column to the user table
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
