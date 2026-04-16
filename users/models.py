from io import BytesIO
import random

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.files.base import ContentFile
from django.db import models
from PIL import Image, ImageDraw, ImageFont

from users.managers import UserManager


def avatar_upload_path(instance, filename):
    return f"avatars/{instance.email}_{filename}"


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=124)
    surname = models.CharField(max_length=124)
    avatar = models.ImageField(upload_to=avatar_upload_path, blank=True)
    phone = models.CharField(max_length=12, blank=True, null=True, unique=True)
    github_url = models.URLField(blank=True)
    about = models.CharField(max_length=256, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    favorites = models.ManyToManyField(
        "projects.Project",
        related_name="interested_users",
        blank=True,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name", "surname"]

    objects = UserManager()

    def __str__(self):
        return f"{self.name} {self.surname}".strip() or self.email

    def _generate_avatar(self):
        initial = (self.name[:1] if self.name else "U").upper()
        colors = [
            "#DEE7FF",
            "#DFF3E3",
            "#FDECC8",
            "#F5E4FF",
            "#E6F7F5",
        ]
        image = Image.new("RGB", (256, 256), random.choice(colors))
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default(size=110)
        bbox = draw.textbbox((0, 0), initial, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (256 - text_w) / 2
        y = (256 - text_h) / 2 - 10
        draw.text((x, y), initial, fill="#263238", font=font)

        output = BytesIO()
        image.save(output, format="PNG")
        output.seek(0)
        filename = f"generated_{self.email.replace('@', '_at_')}.png"
        self.avatar.save(filename, ContentFile(output.read()), save=False)

    def save(self, *args, **kwargs):
        if not self.avatar:
            self._generate_avatar()
        super().save(*args, **kwargs)
