from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import AgentAd, AgentInquiry, RoommatePost


class RoommatePostForm(forms.ModelForm):
    message = forms.CharField(widget=forms.Textarea(attrs={"rows": 6, "cols": 50, "style": "width:100%;"}))

    class Meta:
        model = RoommatePost
        fields = ["message", "date", "status", "rent", "property_type"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "property_type": forms.Select(
                choices=[
                    ("", "Select type"),
                    ("apartment", "Apartment"),
                    ("house", "House"),
                    ("condo", "Condo"),
                    ("townhouse", "Townhouse"),
                ]
            ),
        }


class CustomRegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = False


class AgentAdForm(forms.ModelForm):
    class Meta:
        model = AgentAd
        fields = [
            "headline",
            "city",
            "state",
            "brokerage",
            "license_number",
            "phone",
            "email",
            "website",
            "bio",
            "specialties",
            "active",
        ]
        widgets = {
            "state": forms.TextInput(
                attrs={
                    "maxlength": 2,
                    "placeholder": "CO",
                }
            ),
            "bio": forms.Textarea(attrs={"rows": 5}),
            "specialties": forms.TextInput(
                attrs={
                    "placeholder": "First-time buyers, condos, rentals",
                }
            ),
        }

    def clean_state(self):
        state = self.cleaned_data.get("state", "")
        return state.strip().upper()

    def clean_city(self):
        city = self.cleaned_data.get("city", "")
        return city.strip()

    def clean_headline(self):
        headline = self.cleaned_data.get("headline", "")
        return headline.strip()

    def clean_brokerage(self):
        brokerage = self.cleaned_data.get("brokerage", "")
        return brokerage.strip()

    def clean_license_number(self):
        license_number = self.cleaned_data.get("license_number", "")
        return license_number.strip()


class AgentInquiryForm(forms.ModelForm):
    class Meta:
        model = AgentInquiry
        fields = ["name", "email", "message"]
        widgets = {
            "message": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": "Tell the agent what you are looking for.",
                }
            ),
        }

    def clean_name(self):
        name = self.cleaned_data.get("name", "")
        return name.strip()

    def clean_message(self):
        message = self.cleaned_data.get("message", "")
        return message.strip()
