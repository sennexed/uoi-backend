import os
import uuid
import random
import string
from datetime import datetime

from flask import Flask, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from PIL import Image, ImageDraw, ImageFont
import requests

app = Flask(__name__)

# ================= CONFIG =================

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ================= MODELS =================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.String(36), unique=True)
    discord_id = db.Column(db.String(50), unique=True)
    user_id = db.Column(db.String(6), unique=True)
    full_name = db.Column(db.String(100))
    nationality = db.Column(db.String(20))
    password = db.Column(db.String(20))
    role = db.Column(db.String(50), default="member")
    status = db.Column(db.String(20), default="pending")
    issued_at = db.Column(db.DateTime)
    last_verified = db.Column(db.DateTime)

class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True)
    value = db.Column(db.String(200))

# ================= INIT =================

with app.app_context():
    db.create_all()

# ================= UTILITIES =================

def generate_user_id():
    return ''.join(random.choices(string.digits, k=6))

def create_card(user, avatar_url):
    width = 800
    height = 500

    card = Image.new("RGB", (width, height), "#eaf4ff")
    draw = ImageDraw.Draw(card)

    try:
        font_big = ImageFont.truetype("arial.ttf", 40)
        font_medium = ImageFont.truetype("arial.ttf", 28)
    except:
        font_big = ImageFont.load_default()
        font_medium = ImageFont.load_default()

    # Title
    draw.text((50, 40), "UOI IDENTIFICATION CARD", fill="black", font=font_big)

    # User Details
    draw.text((50, 150), f"Name: {user.full_name}", fill="black", font=font_medium)
    draw.text((50, 200), f"ID: {user.user_id}", fill="black", font=font_medium)
    draw.text((50, 250), f"Nationality: {user.nationality}", fill="black", font=font_medium)
    draw.text((50, 300), f"Role: {user.role}", fill="black", font=font_medium)

    # Avatar
    if avatar_url:
        try:
            response = requests.get(avatar_url)
            avatar = Image.open(BytesIO(response.content)).resize((200, 200))
            card.paste(avatar, (550, 150))
        except:
            pass

    os.makedirs("cards", exist_ok=True)
    path = f"cards/{user.discord_id}.png"
    card.save(path)

    return path

# ================= ROUTES =================

@app.route("/")
def home():
    return "UOI backend working"

# -------- Setup Registration Channel --------

@app.route("/setup", methods=["POST"])
def setup():
    data = request.json
    channel_id = data.get("channel_id")

    setting = Setting.query.filter_by(key="register_channel").first()

    if not setting:
        setting = Setting(key="register_channel", value=channel_id)
        db.session.add(setting)
    else:
        setting.value = channel_id

    db.session.commit()

    return jsonify({"message": "Setup complete"})

@app.route("/register-channel")
def get_register_channel():
    setting = Setting.query.filter_by(key="register_channel").first()

    if not setting:
        return jsonify({"channel_id": None})

    return jsonify({"channel_id": setting.value})

# -------- Register --------

@app.route("/register", methods=["POST"])
def register():
    data = request.json

    if User.query.filter_by(discord_id=data["discord_id"]).first():
        return jsonify({"error": "Already registered"}), 400

    new_user = User(
        card_id=str(uuid.uuid4()),
        discord_id=data["discord_id"],
        user_id=generate_user_id(),
        full_name=data["full_name"],
        nationality=data["nationality"],
        password=data["password"],
        status="pending"
    )

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "Registration submitted"})

# -------- Approve --------

@app.route("/approve/<discord_id>", methods=["POST"])
def approve(discord_id):
    user = User.query.filter_by(discord_id=discord_id).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    user.status = "active"
    user.issued_at = datetime.utcnow()
    user.last_verified = datetime.utcnow()

    db.session.commit()

    return jsonify({"message": "Approved"})

# -------- Reject --------

@app.route("/reject/<discord_id>", methods=["POST"])
def reject(discord_id):
    user = User.query.filter_by(discord_id=discord_id).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    user.status = "rejected"
    db.session.commit()

    return jsonify({"message": "Rejected"})
    # -------- Revoke --------

@app.route("/revoke/<discord_id>", methods=["POST"])
def revoke(discord_id):
    user = User.query.filter_by(discord_id=discord_id).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.status != "active":
        return jsonify({"error": "Only active users can be revoked"}), 400

    user.status = "revoked"
    user.last_verified = datetime.utcnow()

    db.session.commit()

    return jsonify({"message": "Card revoked successfully"})

# -------- Status --------

@app.route("/status/<discord_id>")
def status(discord_id):
    user = User.query.filter_by(discord_id=discord_id).first()

    if not user:
        return jsonify({"status": "not_registered"})

    return jsonify({"status": user.status})

# -------- Card JSON --------

@app.route("/card/<discord_id>")
def get_card(discord_id):
    user = User.query.filter_by(discord_id=discord_id).first()

    if not user or user.status != "active":
        return jsonify({"error": "Card not available"}), 404

    return jsonify({
        "full_name": user.full_name,
        "nationality": user.nationality,
        "user_id": user.user_id,
        "role": user.role
    })

# -------- Card Image --------

@app.route("/card-image/<discord_id>")
def card_image(discord_id):
    user = User.query.filter_by(discord_id=discord_id).first()

    if not user or user.status != "active":
        return jsonify({"error": "Card not available"}), 404

    avatar_url = request.args.get("avatar")

    path = create_card(user, avatar_url)

    return send_file(path, mimetype="image/png")

# ================= RUN =================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
