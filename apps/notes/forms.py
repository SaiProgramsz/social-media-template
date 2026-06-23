from django import forms
from django.core.exceptions import ValidationError

from .models import NoteSet
from apps.moderation.profanity import contains_profanity


class NoteSetForm(forms.ModelForm):
    class Meta:
        model = NoteSet
        fields = ["title", "subject", "content"]
        widgets = {"content": forms.Textarea(attrs={"rows": 10})}

    def clean_title(self):
        title = self.cleaned_data.get("title", "")
        if contains_profanity(title):
            raise ValidationError("Please remove profanity from the title.")
        return title

    def clean_content(self):
        content = self.cleaned_data.get("content", "")
        if contains_profanity(content):
            raise ValidationError("Please remove profanity and keep notes student-friendly.")
        return content
