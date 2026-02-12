from flask import Flask, request, jsonify, send_file
from database import db
from models import User
from card_generator import create_card
from datetime import datetime
import os

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route("/")
def home():
    return "UOI Backend Working"

# Register
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    discord_id = data["discord_id"]

    existing = User.query.filter_by(discord_id=discord_id).first()
    if existing:
        return jsonify({"message": "Already registered"}), 400

    new_user = User(
        discord_id=discord_id,
        full_name=data["full_name"],
        nationality=data["nationality"],
        date_joined=datetime.utcnow().strftime("%d/%m/%Y")
    )

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "Registration submitted"})


# Approve
@app.route("/approve/<discord_id>", methods=["POST"])
def approve(discord_id):
    user = User.query.filter_by(discord_id=discord_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    user.status = "active"
    user.issued_on = datetime.utcnow().strftime("%d/%m/%Y")
    db.session.commit()

    return jsonify({"message": "Approved"})


# Reject
@app.route("/reject/<discord_id>", methods=["POST"])
def reject(discord_id):
    user = User.query.filter_by(discord_id=discord_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    user.status = "rejected"
    db.session.commit()

    return jsonify({"message": "Rejected"})


# Status
@app.route("/status/<discord_id>")
def status(discord_id):
    user = User.query.filter_by(discord_id=discord_id).first()
    if not user:
        return jsonify({"error": "Not found"}), 404

    return jsonify({"status": user.status})


# CARD (returns IMAGE not JSON)
@app.route("/card/<discord_id>")
def card(discord_id):
    user = User.query.filter_by(discord_id=discord_id).first()

    if not user or user.status != "active":
        return jsonify({"error": "Card not available"}), 404

    avatar_url = request.args.get("avatar")
    file_path = create_card(user, avatar_url)

    return send_file(file_path, mimetype="image/png")
