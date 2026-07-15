from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import HearAboutUs, Organization


class OrganizationLoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    remember_me = forms.BooleanField(required=False)

    def clean(self):
        cleaned_data = super().clean()
        email = (cleaned_data.get("email") or "").strip().lower()
        password = cleaned_data.get("password") or ""

        if not email or not password:
            return cleaned_data

        user = authenticate(username=email, password=password)
        if user is None:
            raise forms.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise forms.ValidationError("This account has been deactivated. Please contact IDL.")

        cleaned_data["user"] = user
        return cleaned_data


class OrganizationRegistrationForm(forms.ModelForm):
    confirm_email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = Organization
        fields = [
            "org_name",
            "email",
            "contact_person",
            "correspondence_phone",
            "correspondence_email",
            "logo",
            "hear_about_us",
            "hear_about_us_other",
        ]

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()

        if Organization.objects.filter(email=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists."
            )

        return email

    def clean_correspondence_email(self):
        email = (self.cleaned_data.get("correspondence_email") or "").strip().lower()

        if Organization.objects.filter(correspondence_email=email).exists():
            raise forms.ValidationError(
                "This correspondence email is already in use."
            )

        return email


    def clean_correspondence_phone(self):
        phone = (self.cleaned_data.get("correspondence_phone") or "").strip()

        if Organization.objects.filter(correspondence_phone=phone).exists():
            raise forms.ValidationError(
                "This phone number is already registered."
            )

        return phone


    def clean_confirm_email(self):
        return (self.cleaned_data.get("confirm_email") or "").strip().lower()


    def clean(self):
        cleaned_data = super().clean()

        email = cleaned_data.get("email")
        confirm_email = cleaned_data.get("confirm_email")

        if email and confirm_email and email != confirm_email:
            self.add_error("confirm_email", "Email addresses do not match.")

        hear_about_us = cleaned_data.get("hear_about_us")
        hear_about_us_other = (cleaned_data.get("hear_about_us_other") or "").strip()

        if hear_about_us == HearAboutUs.OTHER and not hear_about_us_other:
            self.add_error(
                "hear_about_us_other",
                "Please specify how you heard about us."
            )

        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match.")

        if password:
            instance = Organization(
                email=email or "",
                org_name=cleaned_data.get("org_name") or ""
            )

            try:
                validate_password(password, instance)
            except ValidationError as exc:
                self.add_error("password", exc)

        return cleaned_data


