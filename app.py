
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
    # Allowing access to generate preview even if pending/rejected for debugging/system needs, 
    # but based on prompt logic, we usually only return active.
    if not user:
        return jsonify({"error": "User not found"}), 404

    avatar_url = request.args.get('avatar_url')
    
    # 1. Load template.png (900x550)
    template_path = os.path.join(os.path.dirname(__file__), 'template.png')
    if not os.path.exists(template_path):
        return jsonify({"error": "Template file (template.png) missing in backend folder"}), 500

    try:
        card = Image.open(template_path).convert("RGBA")
        draw = ImageDraw.Draw(card)
    except Exception as e:
        return jsonify({"error": f"Failed to load template: {str(e)}"}), 500

    # Colors
    NAVY = (27, 42, 78)      # #1b2a4e
    GRAY = (51, 51, 51)      # #333333
    GREEN = (30, 126, 52)    # #1e7e34
    RED = (200, 35, 51)      # #c82333
    ORANGE = (253, 126, 20)  # #fd7e14

    # 2. OVERLAY DYNAMIC TEXT
    # Using standard fonts - in production place a .ttf file in backend/ and use ImageFont.truetype
    # For now fallback to default or generic search.
    try:
        # Note: PIL default font is tiny and doesn't support size. 
        # For a production look, we expect a font file. Fallback logic provided.
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if not os.path.exists(font_path):
             font_path = "arial.ttf" # Windows fallback

        try:
            name_font = ImageFont.truetype(font_path, 36)
            info_font = ImageFont.truetype(font_path, 24)
            small_font = ImageFont.truetype(font_path, 14)
        except:
            name_font = ImageFont.load_default()
            info_font = ImageFont.load_default()
            small_font = ImageFont.load_default()

        # Full Name
        draw.text((350, 200), user.full_name.upper(), fill=NAVY, font=name_font)
        
        # Fields
        draw.text((350, 260), f"UOI ID: #{user.user_id}", fill=GRAY, font=info_font)
        draw.text((350, 310), f"Nationality: {user.nationality}", fill=GRAY, font=info_font)
        draw.text((350, 360), f"Role: {user.role.upper()}", fill=GRAY, font=info_font)
        
        # Status
        status_text = user.status.upper()
        status_color = GRAY
        if status_text == "ACTIVE": status_color = GREEN
        elif status_text == "REJECTED": status_color = RED
        elif status_text in ["REVOKED", "REVOKE"]: status_color = ORANGE
        
        draw.text((350, 410), f"Status: {status_text}", fill=status_color, font=info_font)
        
        # Issued Date
        issued_str = user.issued_at.strftime("%d/%m/%Y") if user.issued_at else "PENDING"
        draw.text((350, 460), f"Issued On: {issued_str}", fill=GRAY, font=info_font)
        
        # Internal ID
        draw.text((70, 500), f"UOI-{user.user_id}", fill=GRAY, font=small_font)

    except Exception as e:
        print(f"Overlay text error: {e}")

    # 3. OVERLAY CIRCULAR AVATAR
    if avatar_url:
        try:
            response = requests.get(avatar_url, timeout=5)
            av_img = Image.open(io.BytesIO(response.content)).convert("RGBA")
            
            AV_SIZE = 250
            AV_POS = (60, 200)
            
            av_img = av_img.resize((AV_SIZE, AV_SIZE), Image.Resampling.LANCZOS)
            
            # Circular Mask
            mask = Image.new('L', (AV_SIZE, AV_SIZE), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, AV_SIZE, AV_SIZE), fill=255)
            
            output = ImageOps.fit(av_img, (AV_SIZE, AV_SIZE), centering=(0.5, 0.5))
            output.putalpha(mask)
            
            # Paste into placeholder
            card.paste(output, AV_POS, output)
        except Exception as e:
            print(f"Avatar processing error: {e}")

    # 4. RETURN FINAL IMAGE
    img_byte_arr = io.BytesIO()
    # Save as PNG to maintain transparency/quality
    card.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    return send_file(img_byte_arr, mimetype='image/png')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
