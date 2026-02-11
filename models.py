import uuid
from datetime import datetime
from database import db

class UserCard(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    discord_id = db.Column(db.String(30), unique=True, nullable=False)

    user_id = db.Column(db.String(6), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    nationality = db.Column(db.String(20), nullable=False)

    role = db.Column(db.String(50), default="member")
    status = db.Column(db.String(20), default="pending")

    password = db.Column(db.String(200), nullable=False)

    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_verified = db.Column(db.DateTime, default=datetime.utcnow)