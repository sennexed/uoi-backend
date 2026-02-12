import os
import random
import requests
from io import BytesIO
from datetime import datetime

from flask import Flask, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)

# =============================
# DATABASE CONFIG
# =============================

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# =============================
# DATABASE MODEL
# =============================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discord_id = db.Column(db.String(30), unique=True, nullable=False)
    full_name = db.Column(db.String(120))
    nationality = db.Column(db.String(50))
    user_id = db.Column(db.String(6), unique=True)
    role = db.Column(db.String(50), default="Member")
    status = db.Column(db.String(20), default="under_review")
    issued_at = db.Column(db.DateTime)
    password = db.Column(db.String(120))


with app.app_context():
    db.create_all()


# =============================
# CARD GENERATOR
# =============================

def generate_card(user, avatar_url):
    width, height = 900, 550
    card = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(card)

    try:
        font_title = ImageFont.truetype("arial.ttf", 60)
        font_text = ImageFont.truetype("arial.ttf", 40)
        font_small = ImageFont.truetype("arial.ttf", 32)
    except:
        font_title = ImageFont.load_default()
        font_text = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Header
    draw.text((50, 40), "UNION OF INDIANS", fill="#003366", font=font_title)
    draw.text((50, 120), "Official Identification Card", fill="gray", font=font_small)

    # Avatar
    response = requests.get(avatar_url)
    avatar = Image.open(BytesIO(response.content)).convert("RGB")
    avatar = avatar.resize((250, 250))

    mask = Image.new("L", (250, 250), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 250, 250), fill=255)

    card.paste(avatar, (60, 200), mask)

    # Details
    x = 350
    y = 200

    draw.text((x, y), user.full_name, fill="black", font=font_text)
    y += 70
    draw.text((x, y), f"UOI ID: {user.user_id}", fill="black", font=font_small)
    y += 60
    draw.text((x, y), f"Nationality: {user.nationality}", fill="black", font=font_small)
    y += 60
    draw.text((x, y), f"Role: {user.role}", fill="black", font=font_small)
    y += 60
    draw.text((x, y), f"Status: {user.status}", fill="black", font=font_small)
    y += 60
    draw.text((x, y), f"Issued: {user.issued_at.strftime('%Y-%m-%d')}", fill="black", font=font_small)

    if not os.path.exists("cards"):
        os.makedirs("cards")

    file_path = f"cards/{user.discord_id}.png"
    card.save(file_path)

    return file_path


# =============================
# ROUTES
# =============================

@app.route("/")
def home():
    return "UOI Backend Working"


@app.route("/register", methods=["POST"])
def register():
    data = request.json

    existing = User.query.filter_by(discord_id=data["discord_id"]).first()
    if existing:
        return jsonify({"error": "Already registered"}), 400

    new_user = User(
        discord_id=data["discord_id"],
        full_name=data["full_name"],
        nationality=data["nationality"],
        user_id=str(random.randint(100000, 999999)),
        password=data["password"],
        status="under_review"
    )

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "Registration submitted"})


@app.route("/approve/<discord_id>", methods=["POST"])
def approve(discord_id):
    user = User.query.filter_by(discord_id=discord_id).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    user.status = "active"
    user.issued_at = datetime.utcnow()
    db.session.commit()

    return jsonify({"message": "Approved"})


@app.route("/revoke/<discord_id>", methods=["POST"])
def revoke(discord_id):
    user = User.query.filter_by(discord_id=discord_id).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    user.status = "revoked"
    db.session.commit()

    return jsonify({"message": "Revoked"})


@app.route("/status/<discord_id>")
def status(discord_id):
    user = User.query.filter_by(discord_id=discord_id).first()

    if not user:
        return jsonify({"error": "Not registered"}), 404

    return jsonify({"status": user.status})


@app.route("/card/<discord_id>")
def card(discord_id):
    user = User.query.filter_by(discord_id=discord_id).first()

    if not user or user.status != "active":
        return jsonify({"error": "Card not available"}), 404

    avatar_url = request.args.get("avatar")

    file_path = generate_card(user, avatar_url)

    return send_file(file_path, mimetype="image/png")


