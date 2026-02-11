import os
import random
from datetime import datetime

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

app = Flask(__name__)

# ================= DATABASE CONFIG =================

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ================= DATABASE MODEL =================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discord_id = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.String(6), unique=True, nullable=False)
    full_name = db.Column(db.String(100))
    nationality = db.Column(db.String(20))
    role = db.Column(db.String(50), default="Member")
    password = db.Column(db.String(100))
    status = db.Column(db.String(20), default="pending")
    issued_at = db.Column(db.DateTime)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

# ================= UTIL =================

def generate_user_id():
    return str(random.randint(100000, 999999))

def create_card(user, avatar_url):
    width = 900
    height = 550

    img = Image.new("RGB", (width, height), "#0f1e2e")
    draw = ImageDraw.Draw(img)

    # Blue header
    draw.rectangle((0, 0, width, 120), fill="#1f4fa3")

    # Title
    draw.text((30, 35), "UNION OF INDIANS", fill="white")
    draw.text((30, 75), "Official Identification Card", fill="white")

    # Avatar
    response = requests.get(avatar_url)
    avatar = Image.open(BytesIO(response.content)).resize((150, 150))
    img.paste(avatar, (700, 180))

    # Details
    y = 180
    spacing = 50

    draw.text((60, y), f"Name: {user.full_name}", fill="white")
    y += spacing
    draw.text((60, y), f"Nationality: {user.nationality}", fill="white")
    y += spacing
    draw.text((60, y), f"User ID: {user.user_id}", fill="white")
    y += spacing
    draw.text((60, y), f"Role: {user.role}", fill="white")
    y += spacing
    draw.text((60, y), f"Issued: {user.issued_at.strftime('%d-%m-%Y')}", fill="white")

    path = f"/tmp/card_{user.discord_id}.png"
    img.save(path)
    return path

# ================= ROUTES =================

@app.route("/")
def home():
    return "UOI Backend Running"

@app.route("/register", methods=["POST"])
def register():
    data = request.json

    existing = User.query.filter_by(discord_id=data["discord_id"]).first()
    if existing:
        return jsonify({"error": "Already registered"}), 400

    user = User(
        discord_id=data["discord_id"],
        user_id=generate_user_id(),
        full_name=data["full_name"],
        nationality=data["nationality"],
        password=data["password"],
        status="pending"
    )

    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "Request stored"})

@app.route("/approve/<discord_id>", methods=["POST"])
def approve(discord_id):
    user = User.query.filter_by(discord_id=discord_id).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    user.status = "active"
    user.issued_at = datetime.utcnow()
    db.session.commit()

    return jsonify({"message": "Approved"})

@app.route("/card/<discord_id>")
def get_card(discord_id):
    user = User.query.filter_by(discord_id=discord_id).first()

    if not user or user.status != "active":
        return jsonify({"error": "Card not available"}), 404

    avatar_url = request.args.get("avatar")

    card_path = create_card(user, avatar_url)

    return jsonify({
        "full_name": user.full_name,
        "nationality": user.nationality,
        "user_id": user.user_id,
        "role": user.role,
        "card_path": card_path
    })

# ================= STARTUP =================

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
