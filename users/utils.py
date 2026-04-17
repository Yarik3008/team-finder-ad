from io import BytesIO
import random

from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont

AVATAR_BACKGROUND_COLORS = (
    "#DEE7FF",
    "#DFF3E3",
    "#FDECC8",
    "#F5E4FF",
    "#E6F7F5",
)
AVATAR_SIZE = 256
AVATAR_FONT_SIZE = 110
AVATAR_TEXT_COLOR = "#263238"
AVATAR_TEXT_VERTICAL_OFFSET = -10


def generate_avatar(user):
    initial = (user.name[:1] if user.name else "U").upper()
    image = Image.new("RGB", (AVATAR_SIZE, AVATAR_SIZE), random.choice(AVATAR_BACKGROUND_COLORS))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=AVATAR_FONT_SIZE)
    bbox = draw.textbbox((0, 0), initial, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (AVATAR_SIZE - text_w) / 2
    y = (AVATAR_SIZE - text_h) / 2 + AVATAR_TEXT_VERTICAL_OFFSET
    draw.text((x, y), initial, fill=AVATAR_TEXT_COLOR, font=font)

    output = BytesIO()
    image.save(output, format="PNG")
    output.seek(0)
    filename = f"generated_{user.email.replace('@', '_at_')}.png"
    user.avatar.save(filename, ContentFile(output.read()), save=False)
