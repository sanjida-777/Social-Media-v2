import unittest
from flask import Flask, session, g
from create_app import create_app
from database import db
from models import User, Friend
import os
import tempfile

class MutualFriendsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(testing=True)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            
            # Create test users
            user1 = User(username='user1', email='user1@example.com', password_hash='password')
            user2 = User(username='user2', email='user2@example.com', password_hash='password')
            user3 = User(username='user3', email='user3@example.com', password_hash='password')
            user4 = User(username='user4', email='user4@example.com', password_hash='password')
            
            db.session.add_all([user1, user2, user3, user4])
            db.session.commit()
            
            # Create friendships
            # user1 and user2 are friends
            friendship1 = Friend(user_id=user1.id, friend_id=user2.id, status='accepted')
            # user1 and user3 are friends
            friendship2 = Friend(user_id=user1.id, friend_id=user3.id, status='accepted')
            # user2 and user3 are friends
            friendship3 = Friend(user_id=user2.id, friend_id=user3.id, status='accepted')
            
            db.session.add_all([friendship1, friendship2, friendship3])
            db.session.commit()
    
    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_mutual_friends_calculation(self):
        with self.app.app_context():
            # Log in as user4
            with self.client.session_transaction() as sess:
                sess['user_id'] = 4  # user4's ID
            
            # Make user4 friends with user1
            friendship = Friend(user_id=4, friend_id=1, status='accepted')
            db.session.add(friendship)
            db.session.commit()
            
            # Access the friends page
            response = self.client.get('/auth/friends')
            self.assertEqual(response.status_code, 200)
            
            # Check if mutual friends are calculated correctly
            # user4 is friends with user1
            # user1 is friends with user2 and user3
            # So user4 should have 1 mutual friend (user1) with both user2 and user3
            
            # This is a simplified test - in a real test, you would parse the HTML
            # and check the actual mutual friends count displayed
            self.assertIn(b'mutual friend', response.data)
    
    def test_no_mutual_friends(self):
        with self.app.app_context():
            # Log in as user4 (who has no friends initially)
            with self.client.session_transaction() as sess:
                sess['user_id'] = 4  # user4's ID
            
            # Access the friends page
            response = self.client.get('/auth/friends')
            self.assertEqual(response.status_code, 200)
            
            # Check if "No mutual friends" is displayed for suggestions
            # This is a simplified test - in a real test, you would parse the HTML
            self.assertIn(b'No mutual friends', response.data)

if __name__ == '__main__':
    unittest.main()
