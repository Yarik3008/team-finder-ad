import re
from urllib.parse import urlparse

from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


def normalize_phone(phone):
    phone = (phone or "").strip()
    if not phone:
        return None
    if re.fullmatch(r"8\d{10}", phone):
        return "+7" + phone[1:]
    if re.fullmatch(r"\+7\d{10}", phone):
        return phone
    raise forms.ValidationError("Телефон должен быть в формате 8XXXXXXXXXX или +7XXXXXXXXXX.")


def validate_github_url(value):
    if not value:
        return value
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        raise forms.ValidationError("Введите корректную ссылку.")
    host = parsed.netloc.lower()
    if host not in {"github.com", "www.github.com"}:
        raise forms.ValidationError("Ссылка должна вести на Github.")
    return value


class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Пароль")

    class Meta:
        model = User
        fields = ["name", "surname", "email", "password"]
        labels = {
            "name": "Имя",
            "surname": "Фамилия",
            "email": "Email",
        }

    def save(self, commit=True):
        user = User(
            name=self.cleaned_data["name"],
            surname=self.cleaned_data["surname"],
            email=self.cleaned_data["email"],
        )
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(widget=forms.PasswordInput, label="Пароль")


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["name", "surname", "avatar", "about", "phone", "github_url"]
        labels = {
            "name": "Имя",
            "surname": "Фамилия",
            "avatar": "Аватар",
            "about": "О себе",
            "phone": "Телефон",
            "github_url": "GitHub",
        }

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data.get("phone"))
        if not phone:
            return phone
        qs = User.objects.filter(phone=phone)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Такой номер уже используется другим пользователем.")
        return phone

    def clean_github_url(self):
        return validate_github_url(self.cleaned_data.get("github_url"))
