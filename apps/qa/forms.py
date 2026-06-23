from django import forms
from django.core.exceptions import ValidationError

from .models import Answer, Question
from apps.moderation.profanity import contains_profanity


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ["subject", "title", "body"]
        widgets = {"body": forms.Textarea(attrs={"rows": 8})}

    def clean_title(self):
        title = self.cleaned_data.get("title", "")
        if contains_profanity(title):
            raise ValidationError("Please remove profanity from the title.")
        return title

    def clean_body(self):
        body = self.cleaned_data.get("body", "")
        if contains_profanity(body):
            raise ValidationError("Please remove profanity and keep it student-friendly.")
        return body


class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ["body"]
        widgets = {"body": forms.Textarea(attrs={"rows": 6})}

    def clean_body(self):
        body = self.cleaned_data.get("body", "")
        if contains_profanity(body):
            raise ValidationError("Please remove profanity and keep it student-friendly.")
        return body
