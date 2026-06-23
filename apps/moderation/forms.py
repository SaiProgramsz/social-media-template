from __future__ import annotations

from django import forms

from .models import Block, Report


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ["reason", "details", "content_type", "object_id"]
        widgets = {
            "details": forms.Textarea(attrs={"rows": 5, "placeholder": "What happened? Include context/time."}),
            "content_type": forms.HiddenInput(),
            "object_id": forms.HiddenInput(),
        }


class BlockForm(forms.ModelForm):
    class Meta:
        model = Block
        fields = []

