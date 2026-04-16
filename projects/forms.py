from urllib.parse import urlparse

from django import forms

from projects.models import Project


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["name", "description", "github_url", "status"]
        labels = {
            "name": "Название проекта",
            "description": "Описание проекта",
            "github_url": "Ссылка на GitHub",
            "status": "Статус",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = [
            (Project.STATUS_OPEN, "Открыт"),
            (Project.STATUS_CLOSED, "Закрыт"),
        ]

    def clean_github_url(self):
        value = self.cleaned_data.get("github_url")
        if not value:
            return value
        parsed = urlparse(value)
        if not parsed.scheme or not parsed.netloc:
            raise forms.ValidationError("Введите корректную ссылку.")
        if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
            raise forms.ValidationError("Ссылка должна вести на Github.")
        return value
