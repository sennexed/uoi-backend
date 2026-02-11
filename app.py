import os
import random
from flask import Flask, request, jsonify
from database import db
from models import UserCard

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()

def generate_user_id():
    return str(random.randint(100000, 999999))

@app.route("/register", methods=["POST"])
def register():
    data = request.json

    if len(data["password"].split()) != 6:
        return jsonify({"error": "Password must be exactly 6 words"}), 400

    user = UserCard(
        discord_id=data["discord_id"],
        user_id=generate_user_id(),
        full_name=data["full_name"],
        nationality=data["nationality"],
        password=data["password"]
    )

    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "Request submitted"})

@app.route("/approve/<discord_id>", methods=["POST"])
def approve(discord_id):
    user = UserCard.query.filter_by(discord_id=discord_id).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    user.status = "active"
    db.session.commit()

    return jsonify({"message": "Approved"})

@app.route("/card/<discord_id>")
def get_card(discord_id):
    user = UserCard.query.filter_by(discord_id=discord_id).first()

    if not user:
        return jsonify({"error": "Not found"}), 404

    return jsonify({
        "user_id": user.user_id,
        "full_name": user.full_name,
        "nationality": user.nationality,
        "role": user.role,
        "status": user.status,
        "issued_at": user.issued_at
    })