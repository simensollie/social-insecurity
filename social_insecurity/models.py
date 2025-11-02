"""
User model for Flask-Login integration.
"""

from flask_login import UserMixin
from social_insecurity import sqlite


class User(UserMixin):
    """User model compatible with Flask-Login."""
    
    def __init__(self, id, username, first_name, last_name, password):
        self.id = id
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.password = password
    
    @staticmethod
    def get(user_id):
        """Get a user by ID from the database."""
        user_data = sqlite.query(
            "SELECT * FROM Users WHERE id = ?;", 
            user_id, 
            one=True
        )
        if user_data:
            return User(
                user_data['id'],
                user_data['username'],
                user_data['first_name'],
                user_data['last_name'],
                user_data['password']
            )
        return None