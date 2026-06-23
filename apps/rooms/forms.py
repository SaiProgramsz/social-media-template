from django import forms
from django.core.exceptions import ValidationError

from .models import PomodoroSession, RoomMessage, StudyRoom
from apps.moderation.profanity import contains_profanity


class StudyRoomForm(forms.ModelForm):
    class Meta:
        model = StudyRoom
        fields = ["title", "subject", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}

    def clean_title(self):
        title = self.cleaned_data.get("title", "")
        if contains_profanity(title):
            raise ValidationError("Please remove profanity from the room title.")
        return title

    def clean_description(self):
        description = self.cleaned_data.get("description", "")
        if contains_profanity(description):
            raise ValidationError("Please remove profanity from the room description.")
        return description


class RoomMessageForm(forms.ModelForm):
    class Meta:
        model = RoomMessage
        fields = ["text"]
        widgets = {"text": forms.Textarea(attrs={"rows": 3, "placeholder": "Ask a question or share a quick tip..."})}

    def clean_text(self):
        text = self.cleaned_data.get("text", "")
        if contains_profanity(text):
            raise ValidationError("Please remove profanity and keep chat student-friendly.")
        return text


class PomodoroSessionForm(forms.ModelForm):
    class Meta:
        model = PomodoroSession
        fields = ["focus_minutes", "break_minutes", "note"]
        widgets = {"note": forms.TextInput(attrs={"placeholder": "e.g. Algebra practice"})}
