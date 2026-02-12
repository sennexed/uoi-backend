
import os
import random
import string
import io
import bcrypt
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from models import db, User
from PIL import Image, ImageDraw, ImageFont, ImageOps
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
        if User.query.filter_by(discord_id=data['discord_id']).first():
            return jsonify({"error": "User already registered"}), 400

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

@app.route('/generate_card/<discord_id>', methods=['GET'])
def generate_card(discord_id):
    user = User.query.filter_by(discord_id=discord_id).first()
    if not user or user.status != "active":
        return jsonify({"error": "Card not available or user not active"}), 403

    avatar_url = request.args.get('avatar_url')
    
    # Create Canvas
    width, height = 800, 500
    card = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(card)

    # Theme Colors
    BLUE_DARK = (20, 50, 120)
    BLUE_LIGHT = (230, 240, 255)

    # Background Design
    draw.rectangle([0, 0, width, 120], fill=BLUE_DARK)
    draw.rectangle([0, 120, width, height], fill=BLUE_LIGHT)

    # Watermark
    try:
        wm_font = ImageFont.load_default() # In production, use a TTF font
        draw.text((width//2, height//2), "UNION OF INDIANS", fill=(200, 210, 230), font=wm_font, anchor="mm")
    except: pass

    # Header Text
    draw.text((width//2, 60), "UNION OF INDIANS - MEMBERSHIP CARD", fill=(255, 255, 255), anchor="mm")

    # Avatar
    if avatar_url:
        try:
            response = requests.get(avatar_url)
            av_img = Image.open(io.BytesIO(response.content)).convert("RGBA")
            av_img = av_img.resize((150, 150))
            
            mask = Image.new('L', (150, 150), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, 150, 150), fill=255)
            
            output = ImageOps.fit(av_img, (150, 150), centering=(0.5, 0.5))
            output.putalpha(mask)
            
            card.paste(output, (50, 160), output)
        except:
            draw.ellipse((50, 160, 200, 310), outline=BLUE_DARK, width=2)

    # Fields
    x_offset = 240
    y_start = 160
    line_height = 40
    
    fields = [
        ("Full Name", user.full_name),
        ("UOI ID", user.user_id),
        ("Nationality", user.nationality),
        ("Role", user.role.upper()),
        ("Status", user.status.upper()),
        ("Issued Date", user.issued_at.strftime("%Y-%m-%d") if user.issued_at else "N/A"),
        ("Discord ID", user.discord_id)
    ]

    for i, (label, val) in enumerate(fields):
        draw.text((x_offset, y_start + i * line_height), f"{label}:", fill=BLUE_DARK)
        draw.text((x_offset + 150, y_start + i * line_height), str(val), fill=(0, 0, 0))

    # Save to buffer
    img_byte_arr = io.BytesIO()
    card.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    return send_file(img_byte_arr, mimetype='image/png')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    
