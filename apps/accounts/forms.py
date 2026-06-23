from django import forms

from .models import User


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["display_name", "bio", "profile_image", "school", "major", "grade_level"]
        widgets = {
            "bio": forms.Textarea(
                attrs={"rows": 6, "placeholder": "A short bio about you (subjects, goals, exam prep...)."}
            )
        }
