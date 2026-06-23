from django import forms
from django.core.exceptions import ValidationError

from .models import Post
from apps.moderation.profanity import contains_profanity


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["subject", "text"]
        widgets = {"text": forms.Textarea(attrs={"rows": 4, "placeholder": "What did you study today? Share a tip or summary."})}

    def clean_text(self):
        text = self.cleaned_data.get("text", "")
        if contains_profanity(text):
            raise ValidationError("Please remove profanity and keep it student-friendly.")
        return text
