from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import os

def create_card(user, avatar_url):
    width, height = 900, 550
    card = Image.new("RGB", (width, height), (15, 40, 80))
    draw = ImageDraw.Draw(card)

    try:
        font_big = ImageFont.truetype("arial.ttf", 50)
        font_small = ImageFont.truetype("arial.ttf", 32)
    except:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Avatar
    if avatar_url:
        response = requests.get(avatar_url)
        avatar = Image.open(BytesIO(response.content)).resize((200, 200))
        card.paste(avatar, (60, 170))

    # Text
    draw.text((300, 150), "UOI IDENTIFICATION", font=font_big, fill="white")
    draw.text((300, 230), f"Name: {user.full_name}", font=font_small, fill="white")
    draw.text((300, 280), f"ID: {user.user_id}", font=font_small, fill="white")
    draw.text((300, 330), f"Nationality: {user.nationality}", font=font_small, fill="white")
    draw.text((300, 380), f"Role: {user.role}", font=font_small, fill="white")

    if not os.path.exists("cards"):
        os.makedirs("cards")

    path = f"cards/{user.discord_id}.png"
    card.save(path)
    return path
