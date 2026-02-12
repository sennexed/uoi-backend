
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

def add_rounded_corners(im, rad):
    circle = Image.new('L', (rad * 2, rad * 2), 0)
    draw = ImageDraw.Draw(circle)
    draw.ellipse((0, 0, rad * 2 - 1, rad * 2 - 1), fill=255)
    alpha = Image.new('L', im.size, 255)
    w, h = im.size
    alpha.paste(circle.crop((0, 0, rad, rad)), (0, 0))
    alpha.paste(circle.crop((0, rad, rad, rad * 2)), (0, h - rad))
    alpha.paste(circle.crop((rad, 0, rad * 2, rad)), (w - rad, 0))
    alpha.paste(circle.crop((rad, rad, rad * 2, rad * 2)), (w - rad, h - rad))
    im.putalpha(alpha)
    return im

@app.route('/generate_card/<discord_id>', methods=['GET'])
def generate_card(discord_id):
    user = User.query.filter_by(discord_id=discord_id).first()
    if not user or user.status != "active":
        return jsonify({"error": "Card not available or user not active"}), 403

    avatar_url = request.args.get('avatar_url')
    
    # Constants
    WIDTH, HEIGHT = 1200, 700
    NAVY_BLUE = (20, 30, 70)
    OFF_WHITE = (245, 245, 250)
    TEXT_COLOR = (40, 40, 40)
    BORDER_COLOR = (200, 200, 200)
    ORANGE = (255, 153, 51)
    GREEN = (19, 136, 8)
    
    # Create Main Canvas with Shadow Padding
    bg = Image.new('RGBA', (WIDTH + 40, HEIGHT + 40), (255, 255, 255, 0))
    shadow = Image.new('RGBA', (WIDTH, HEIGHT), (0, 0, 0, 40))
    bg.paste(shadow, (25, 25))
    bg = bg.filter(ImageFilter.GaussianBlur(10))

    # Actual Card Image
    card = Image.new('RGB', (WIDTH, HEIGHT), color=(255, 255, 255))
    draw = ImageDraw.Draw(card)

    # 1. Premium White Textured Background (Subtle Gradient/Texture simulated by light gray noise)
    draw.rectangle([0, 0, WIDTH, HEIGHT], fill=OFF_WHITE)
    
    # 2. Top Header Section
    draw.rectangle([0, 0, WIDTH, 160], fill=NAVY_BLUE)
    
    # 3. Header Text
    try:
        # Note: Default font is tiny. In a real environment, load a TTF.
        draw.text((WIDTH // 2, 60), "UNION OF INDIANS", fill=(255, 255, 255), anchor="mm")
        draw.text((WIDTH // 2, 110), "OFFICIAL IDENTIFICATION CARD", fill=(200, 210, 255), anchor="mm")
    except: pass

    # Logo Placeholder
    draw.ellipse((WIDTH - 140, 30, WIDTH - 40, 130), outline=(255, 255, 255), width=2)
    draw.text((WIDTH - 90, 80), "UOI", fill=(255, 255, 255), anchor="mm")

    # 4. Tricolor Stripe
    stripe_y = 160
    stripe_h = 10
    draw.rectangle([0, stripe_y, WIDTH, stripe_y + stripe_h], fill=ORANGE)
    draw.rectangle([0, stripe_y + stripe_h, WIDTH, stripe_y + stripe_h * 2], fill=(255, 255, 255))
    draw.rectangle([0, stripe_y + stripe_h * 2, WIDTH, stripe_y + stripe_h * 3], fill=GREEN)

    # 5. Left Section: Circular Avatar
    AVATAR_SIZE = 300
    AVATAR_X, AVATAR_Y = 80, 230
    if avatar_url:
        try:
            response = requests.get(avatar_url)
            av_img = Image.open(io.BytesIO(response.content)).convert("RGBA")
            av_img = av_img.resize((AVATAR_SIZE, AVATAR_SIZE))
            
            mask = Image.new('L', (AVATAR_SIZE, AVATAR_SIZE), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, AVATAR_SIZE, AVATAR_SIZE), fill=255)
            
            output = ImageOps.fit(av_img, (AVATAR_SIZE, AVATAR_SIZE), centering=(0.5, 0.5))
            output.putalpha(mask)
            
            # Double Border for Avatar
            draw.ellipse((AVATAR_X - 5, AVATAR_Y - 5, AVATAR_X + AVATAR_SIZE + 5, AVATAR_Y + AVATAR_SIZE + 5), outline=NAVY_BLUE, width=3)
            draw.ellipse((AVATAR_X - 10, AVATAR_Y - 10, AVATAR_X + AVATAR_SIZE + 10, AVATAR_Y + AVATAR_SIZE + 10), outline=BORDER_COLOR, width=1)
            
            card.paste(output, (AVATAR_X, AVATAR_Y), output)
        except:
            draw.ellipse((AVATAR_X, AVATAR_Y, AVATAR_X + AVATAR_SIZE, AVATAR_Y + AVATAR_SIZE), outline=NAVY_BLUE, width=2)

    # Internal Card ID below avatar
    draw.text((AVATAR_X + AVATAR_SIZE // 2, AVATAR_Y + AVATAR_SIZE + 30), f"ID: UOI-{user.user_id}", fill=NAVY_BLUE, anchor="mm")

    # 6. Right Section: User Data
    INFO_X = 480
    INFO_Y = 240
    LINE_SPACE = 55
    
    # Faint Watermark
    draw.text((WIDTH - 250, HEIGHT - 250), "UOI", fill=(230, 230, 230), anchor="mm")

    data_fields = [
        ("NAME", user.full_name.upper()),
        ("UOI ID", f"#{user.user_id}"),
        ("NATIONALITY", user.nationality),
        ("SERVER ROLE", user.role.upper()),
        ("STATUS", user.status.upper()),
        ("JOINED", user.created_at.strftime("%b %d, %Y")),
        ("ISSUED ON", user.issued_at.strftime("%d/%m/%Y") if user.issued_at else "N/A"),
        ("DISCORD ID", user.discord_id)
    ]

    for i, (label, val) in enumerate(data_fields):
        y_pos = INFO_Y + (i * LINE_SPACE)
        draw.text((INFO_X, y_pos), f"{label}:", fill=(100, 100, 100))
        
        val_color = TEXT_COLOR
        if label == "STATUS":
            val_color = GREEN if user.status == "active" else (200, 0, 0)
        
        draw.text((INFO_X + 180, y_pos), str(val), fill=val_color)

    # 7. Bottom Strip
    BOTTOM_Y = HEIGHT - 60
    draw.line([50, BOTTOM_Y, WIDTH - 50, BOTTOM_Y], fill=GREEN, width=2)
    draw.text((WIDTH // 2, BOTTOM_Y + 30), "Verified by UOI Authority", fill=(120, 120, 120), anchor="mm")

    # Finalize with Rounded Corners
    card = card.convert("RGBA")
    card = add_rounded_corners(card, 40)
    
    # Paste the card onto the shadow background
    final_img = Image.new('RGBA', (WIDTH + 40, HEIGHT + 40), (0,0,0,0))
    final_img.paste(bg, (0, 0)) # The blurred shadow
    final_img.paste(card, (20, 20), card)

    # Save and send
    img_byte_arr = io.BytesIO()
    final_img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    return send_file(img_byte_arr, mimetype='image/png')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
