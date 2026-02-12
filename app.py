from flask import Flask, request, jsonify, send_file
from models import db, User
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
    return "UOI backend working"

# REGISTER
@app.route("/register", methods=["POST"])
def register():
    data = request.json

    existing = User.query.filter_by(discord_id=data["discord_id"]).first()
    if existing:
        return jsonify({"error": "Already registered"}), 400

    user = User(
        discord_id=data["discord_id"],
        full_name=data["full_name"],
        nationality=data["nationality"]
    )

    user.generate_public_id()
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "Registered successfully"})

# STATUS
@app.route("/status/<discord_id>")
def status(discord_id):
    user = User.query.filter_by(discord_id=discord_id).first()
    if not user:
        return jsonify({"error": "Not found"}), 404

    return jsonify({"status": user.status})

# APPROVE
@app.route("/approve/<discord_id>", methods=["POST"])
def approve(discord_id):
    user = User.query.filter_by(discord_id=discord_id).first()
    if not user:
        return jsonify({"error": "Not found"}), 404

    user.status = "active"
    user.issued_at = datetime.utcnow()
    user.last_verified = datetime.utcnow()
    db.session.commit()

    return jsonify({"message": "Approved"})

# REJECT
@app.route("/reject/<discord_id>", methods=["POST"])
def reject(discord_id):
    user = User.query.filter_by(discord_id=discord_id).first()
    if not user:
        return jsonify({"error": "Not found"}), 404

    user.status = "rejected"
    db.session.commit()

    return jsonify({"message": "Rejected"})

# REVOKE
@app.route("/revoke/<discord_id>", methods=["POST"])
def revoke(discord_id):
    user = User.query.filter_by(discord_id=discord_id).first()
    if not user:
        return jsonify({"error": "Not found"}), 404

    user.status = "revoked"
    db.session.commit()

    return jsonify({"message": "Revoked"})

# CARD IMAGE
@app.route("/card/<discord_id>")
def get_card(discord_id):
    user = User.query.filter_by(discord_id=discord_id).first()

    if not user or user.status != "active":
        return jsonify({"error": "Card not available"}), 404

    avatar_url = request.args.get("avatar")

    card_path = create_card(user, avatar_url)

    return send_file(card_path, mimetype="image/png")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
