
import os
import random
import string
import io
import bcrypt
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from models import db, User, GuildConfig
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
import requests

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL').replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

def generate_public_id():
    while True:
        pid = ''.join(random.choices(string.digits, k=6))
        if not User.query.filter_by(user_id=pid).first():
            return pid

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    try:
        existing_user = User.query.filter_by(discord_id=data['discord_id']).first()
        
        # Check existing user status
        if existing_user:
            if existing_user.status == "active":
                return jsonify({"error": "User already has an active ID"}), 400
            if existing_user.status == "pending":
                return jsonify({"error": "Registration already pending"}), 400
            
            # If status is "rejected" or "revoked", allow updating the record
            if existing_user.status in ["rejected", "revoked"]:
                hashed = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                existing_user.full_name = data['full_name']
                existing_user.nationality = data['nationality']
                existing_user.password_hash = hashed
                existing_user.status = "pending"
                # Keep existing user_id
                db.session.commit()
                return jsonify(existing_user.to_dict()), 200

        # If user does not exist, create new
        hashed = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        new_user = User(
            discord_id=data['discord_id'],
            user_id=generate_public_id(),
            full_name=data['full_name'],
            nationality=data['nationality'],
            password_hash=hashed,
            status="pending"
        )
        db.session.add(new_user)
        db.session.commit()
        return jsonify(new_user.to_dict()), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/status/<discord_id>', methods=['GET'])
def get_status(discord_id):
    user = User.query.filter_by(discord_id=discord_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"status": user.status, "user": user.to_dict()}), 200

@app.route('/update_status', methods=['POST'])
def update_status():
    data = request.json
    user = User.query.filter_by(discord_id=data['discord_id']).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    user.status = data['status']
    if data['status'] == "active":
        user.issued_at = datetime.utcnow()
    
    db.session.commit()
    return jsonify(user.to_dict()), 200

@app.route('/config/<guild_id>', methods=['GET'])
def get_config(guild_id):
    config = GuildConfig.query.filter_by(guild_id=guild_id).first()
    if not config:
        return jsonify({"error": "Config not found"}), 404
    return jsonify(config.to_dict()), 200

@app.route('/config', methods=['POST'])
def set_config():
    data = request.json
    guild_id = data.get('guild_id')
    config = GuildConfig.query.filter_by(guild_id=guild_id).first()
    
    if not config:
        config = GuildConfig(guild_id=guild_id)
        db.session.add(config)
    
    config.registration_channel_id = data.get('registration_channel_id')
    config.approval_channel_id = data.get('approval_channel_id')
    
    db.session.commit()
    return jsonify(config.to_dict()), 200

@app.route('/generate_card/<discord_id>', methods=['GET'])
def generate_card(discord_id):
    user = User.query.filter_by(discord_id=discord_id).first()
    if not user or user.status != "active":
        return jsonify({"error": "Card not available or user not active"}), 403

    avatar_url = request.args.get('avatar_url')
    
    # 1. Load template.png
    # Path relative to backend/app.py
    template_path = os.path.join(os.path.dirname(__file__), 'template.png')
    if not os.path.exists(template_path):
        return jsonify({"error": "Template file (template.png) missing in backend folder"}), 500

    try:
        card = Image.open(template_path).convert("RGBA")
        draw = ImageDraw.Draw(card)
    except Exception as e:
        return jsonify({"error": f"Failed to load template: {str(e)}"}), 500

    # 2. FIXED COORDINATES (Adjust these based on your specific template.png layout)
    # These coordinates assume a high-res template (approx 1200x700).
    POSITIONS = {
        "avatar": (80, 230, 300),   # (x, y, size)
        "full_name": (480, 240),
        "uoi_id": (660, 295),       # Label-value split often needs offset
        "nationality": (660, 350),
        "role": (660, 405),
        "status": (660, 460),
        "joined": (660, 515),
        "issued": (660, 570),
        "internal_id": (230, 560)   # Alphanumeric ID below avatar
    }

    # 3. OVERLAY DYNAMIC FIELDS
    # Using default font. In production, consider loading a custom TTF for premium look.
    # Note: Pillow default font doesn't support size, usually you'd use ImageFont.truetype('font.ttf', 32)
    try:
        # Placeholder for text rendering - adjust labels and values to match template labels
        draw.text(POSITIONS["full_name"], user.full_name.upper(), fill=(40, 40, 40))
        draw.text(POSITIONS["uoi_id"], f"#{user.user_id}", fill=(40, 40, 40))
        draw.text(POSITIONS["nationality"], user.nationality, fill=(40, 40, 40))
        draw.text(POSITIONS["role"], user.role.upper(), fill=(40, 40, 40))
        
        # Color-coded status
        status_color = (19, 136, 8) if user.status == "active" else (200, 0, 0)
        draw.text(POSITIONS["status"], user.status.upper(), fill=status_color)
        
        draw.text(POSITIONS["joined"], user.created_at.strftime("%b %d, %Y"), fill=(40, 40, 40))
        draw.text(POSITIONS["issued"], user.issued_at.strftime("%d/%m/%Y") if user.issued_at else "N/A", fill=(40, 40, 40))
        
        # Internal Card ID (Internal Card ID)
        draw.text(POSITIONS["internal_id"], f"UOI-{user.user_id}", fill=(20, 30, 70), anchor="mm")
    except Exception as e:
        print(f"Text overlay error: {e}")

    # 4. OVERLAY CIRCULAR AVATAR
    if avatar_url:
        try:
            response = requests.get(avatar_url, timeout=5)
            av_img = Image.open(io.BytesIO(response.content)).convert("RGBA")
            
            size = POSITIONS["avatar"][2]
            av_img = av_img.resize((size, size))
            
            # Mask for circle
            mask = Image.new('L', (size, size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, size, size), fill=255)
            
            output = ImageOps.fit(av_img, (size, size), centering=(0.5, 0.5))
            output.putalpha(mask)
            
            # Paste avatar onto template
            card.paste(output, (POSITIONS["avatar"][0], POSITIONS["avatar"][1]), output)
        except Exception as e:
            print(f"Avatar processing error: {e}")

    # 5. RETURN FINAL IMAGE
    img_byte_arr = io.BytesIO()
    card.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    return send_file(img_byte_arr, mimetype='image/png')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
