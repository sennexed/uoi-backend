from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import random

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discord_id = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.String(6), unique=True)
    full_name = db.Column(db.String(120))
    nationality = db.Column(db.String(20))
    password = db.Column(db.String(120))
    role = db.Column(db.String(50), default="member")
    status = db.Column(db.String(20), default="pending")
    issued_at = db.Column(db.DateTime)
    last_verified = db.Column(db.DateTime)

    def generate_user_id(self):
        self.user_id = str(random.randint(100000, 999999))
