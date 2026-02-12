from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import os

def create_card(user, avatar_url):

    width, height = 900, 550
    card = Image.new("RGB", (width, height), "#f4f4f4")
    draw = ImageDraw.Draw(card)

    # Fonts
    try:
        font_title = ImageFont.truetype("arial.ttf", 60)
        font_text = ImageFont.truetype("arial.ttf", 40)
        font_small = ImageFont.truetype("arial.ttf", 32)
    except:
        font_title = ImageFont.load_default()
        font_text = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Header
    draw.text((50, 40), "UNION OF INDIANS", fill="black", font=font_title)
    draw.text((50, 120), "Official Identification Card", fill="gray", font=font_small)

    # Download avatar
    response = requests.get(avatar_url)
    avatar = Image.open(BytesIO(response.content)).convert("RGB")
    avatar = avatar.resize((250, 250))

    # Make circular avatar
    mask = Image.new("L", (250, 250), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, 250, 250), fill=255)

    card.paste(avatar, (60, 200), mask)

    # User details
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
    draw.text((start_x, y), f"Issued On: {user.issued_on}", fill="black", font=font_small)

    # Save image
    if not os.path.exists("cards"):
        os.makedirs("cards")

    file_path = f"cards/{user.discord_id}.png"
    card.save(file_path)

    return file_path
