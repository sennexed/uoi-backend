
import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    discord_id = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.String(6), unique=True, nullable=False)  # 6-digit public ID
    full_name = db.Column(db.String(100), nullable=False)
    nationality = db.Column(db.String(20), nullable=False)  # Indian or NRI
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default="member")
    status = db.Column(db.String(20), default="pending")  # pending, active, rejected, revoked
    issued_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "discord_id": self.discord_id,
            "user_id": self.user_id,
            "full_name": self.full_name,
            "nationality": self.nationality,
            "role": self.role,
            "status": self.status,
            "issued_at": self.issued_at.isoformat() if self.issued_at else None,
            "created_at": self.created_at.isoformat()
        }
      
