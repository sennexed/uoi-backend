from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import os
from datetime import datetime


def create_card(user, avatar_url):

    width, height = 900, 550
    card = Image.new("RGB", (width, height), "#f4f4f4")
    draw = ImageDraw.Draw(card)

    # Fonts
    try:
        font_title = ImageFont.truetype("arial.ttf", 60)
        font_text = ImageFont.truetype("arial.ttf", 42)
        font_small = ImageFont.truetype("arial.ttf", 34)
    except:
        font_title = ImageFont.load_default()
        font_text = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Header
    draw.text((50, 40), "UNION OF INDIANS", fill="black", font=font_title)
    draw.text((50, 120), "Official Identification Card", fill="gray", font=font_small)

    # === AVATAR SECTION ===
    avatar_size = 250
    avatar_x = 60
    avatar_y = 200

    if avatar_url:
        try:
            response = requests.get(avatar_url, timeout=5)
            avatar = Image.open(BytesIO(response.content)).convert("RGB")
            avatar = avatar.resize((avatar_size, avatar_size))

            mask = Image.new("L", (avatar_size, avatar_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)

            card.paste(avatar, (avatar_x, avatar_y), mask)

        except:
            # Fallback blank circle if avatar fails
            draw.ellipse(
                (avatar_x, avatar_y,
                 avatar_x + avatar_size, avatar_y + avatar_size),
                fill="gray"
            )

    # === USER DETAILS ===
    start_x = 350
    y = 200

    draw.text((start_x, y), f"{user.full_name}", fill="black", font=font_text)
    y += 70

    draw.text((start_x, y), f"UOI ID: {user.user_id}", fill="black", font=font_small)
    y += 60

    draw.text((start_x, y), f"Nationality: {user.nationality}", fill="black", font=font_small)
    y += 60

    draw.text((start_x, y), f"Role: {user.role}", fill="black", font=font_small)
    y += 60

    draw.text((start_x, y), f"Status: {user.status.capitalize()}", fill="black", font=font_small)
    y += 60

    # Fix issued date formatting
    issued_date = "Not Issued"
    if user.issued_at:
        issued_date = user.issued_at.strftime("%d %B %Y")

    draw.text((start_x, y), f"Issued On: {issued_date}", fill="black", font=font_small)

    # === SAVE TO TEMP (Railway Safe) ===
    file_path = f"/tmp/{user.discord_id}_card.png"
    card.save(file_path)

    return file_path
