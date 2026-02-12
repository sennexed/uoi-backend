import os
from flask import Flask, request, jsonify, send_file
from datetime import datetime
from database import db
from models import User
from card_generator import create_card

app = Flask(__name__)

# =============================
# DATABASE CONFIG
# =============================

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()

# =============================
# HEALTH CHECK
# =============================

@app.route("/")
def home():
    return "UOI Backend Working"

# =============================
# REGISTER USER
# =============================

@app.route("/register", methods=["POST"])
def register():
    try:
        data = request.json

        discord_id = data.get("discord_id")
        full_name = data.get("full_name")
        nationality = data.get("nationality")

        if not discord_id or not full_name or not nationality:
            return jsonify({"error": "Missing fields"}), 400

        existing = User.query.filter_by(discord_id=discord_id).first()
        if existing:
            return jsonify({"error": "Already registered"}), 400

        new_user = User(
            discord_id=discord_id,
            full_name=full_name,
            nationality=nationality,
            status="pending"
        )

        db.session.add(new_user)
        db.session.commit()

        return jsonify({"message": "Registration submitted for review"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =============================
# APPROVE USER
# =============================

@app.route("/approve/<discord_id>", methods=["POST"])
def approve(discord_id):
    try:
        user = User.query.filter_by(discord_id=discord_id).first()

        if not user:
            return jsonify({"error": "User not found"}), 404

        user.status = "active"
        user.user_id = user.generate_user_id()
        user.issued_at = datetime.utcnow()
        user.last_verified = datetime.utcnow()

        db.session.commit()

        return jsonify({"message": "User approved"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =============================
# REJECT USER
# =============================

@app.route("/reject/<discord_id>", methods=["POST"])
def reject(discord_id):
    try:
        user = User.query.filter_by(discord_id=discord_id).first()

        if not user:
            return jsonify({"error": "User not found"}), 404

        db.session.delete(user)
        db.session.commit()

        return jsonify({"message": "User rejected"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =============================
# REVOKE USER
# =============================

@app.route("/revoke/<discord_id>", methods=["POST"])
def revoke(discord_id):
    try:
        user = User.query.filter_by(discord_id=discord_id).first()

        if not user:
            return jsonify({"error": "User not found"}), 404

        user.status = "revoked"
        db.session.commit()

        return jsonify({"message": "Card revoked"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =============================
# CHECK STATUS
# =============================

@app.route("/status/<discord_id>")
def status(discord_id):
    try:
        user = User.query.filter_by(discord_id=discord_id).first()

        if not user:
            return jsonify({"error": "User not found"}), 404

        return jsonify({
            "status": user.status,
            "user_id": user.user_id
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =============================
# GENERATE & SEND CARD IMAGE
# =============================

@app.route("/card/<discord_id>")
def get_card(discord_id):
    try:
        user = User.query.filter_by(discord_id=discord_id).first()

        if not user or user.status != "active":
            return jsonify({"error": "Card not available"}), 404

        avatar_url = request.args.get("avatar")

        card_path = create_card(user, avatar_url)

        return send_file(card_path, mimetype="image/png")

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =============================
# RUN
# =============================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
