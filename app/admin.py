from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from django.utils.html import format_html
from django.contrib import messages
from .models import (
    Facility,
    Organization,
)
from .emails import send_organization_status_email, send_facility_status_email
from .models import Resources
from django.contrib import admin
from .models import Activity, Feedback


@admin.register(Resources)
class ResourcesAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title',)


@admin.register(Organization)
class OrganizationAdmin(UserAdmin):
    model = Organization
    ordering = ("-date_joined",)
    list_display = (
        "email",
        "org_name",
        "status",
        "is_active",
        "is_staff",
        "date_joined",
    )
    list_filter = (
        "status",
        "is_active",
        "is_staff",
        "is_superuser",
        "date_joined",
    )
    search_fields = (
        "email",
        "org_name",
        "contact_person",
        "correspondence_email",
        "correspondence_phone",
    )
    readonly_fields = ("last_login", "date_joined", "updated_at")

    fieldsets = (
        ("Authentication", {"fields": ("email", "password")}),
        ("Organization Profile", {"fields": ("org_name", "status", "rejection_reason", "reviewed_at", "reviewed_by")}),
        (
            "Contact Details",
            {
                "fields": (
                    "contact_person",
                    "correspondence_phone",
                    "correspondence_email",
                    "logo",
                )
            },
        ),
        (
            "Discovery",
            {"fields": ("hear_about_us", "hear_about_us_other")},
        ),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
        ("Important Dates", {"fields": ("last_login", "date_joined", "updated_at")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "org_name",
                    "password1",
                    "password2",
                    "contact_person",
                    "correspondence_phone",
                    "correspondence_email",
                    "hear_about_us",
                    "hear_about_us_other",
                    "status",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        """Override save_model to send email on status change"""
        
        # Check if this is an update (not a new object)
        if change and obj.pk:
            # Get the original object from database
            original = Organization.objects.get(pk=obj.pk)
            original_status = original.status
            new_status = obj.status
            
            # If status has changed
            if original_status != new_status:
                obj.reviewed_by = request.user
                # Save the object first
                super().save_model(request, obj, form, change)
                
                # Send email notification
                if new_status in ['approved', 'rejected']:
                    email_sent = send_organization_status_email(obj, new_status)
                    
                    if email_sent:
                        messages.success(
                            request,
                            f'Organization status updated to "{new_status}" and notification email sent.'
                        )
                    else:
                        messages.warning(
                            request,
                            f'Organization status updated to "{new_status}" but email notification failed.'
                        )
                return
        
        # Default save for new objects or status didn't change
        super().save_model(request, obj, form, change)


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "organization",
        "county",
        "sub_county",
        "status",
        "advertise_tier",
        "submitted_at",
        "updated_at",
    )
    list_filter = (
        "status",
        "advertise_tier",
        "registration_status",
        "org_type",
        "funding_source",
        "is_youth_org",
        "is_disability_org",
        "is_women_led",
        "submitted_at",
        "updated_at",
    )
    search_fields = (
        "name",
        "organization__org_name",
        "organization__email",
        "county",
        "sub_county",
        "public_email",
    )
    autocomplete_fields = ("organization", "reviewed_by")
    readonly_fields = ("submitted_at", "updated_at")

    fieldsets = (
        ("Owner", {"fields": ("organization",)}),
        (
            "Step 1 - Basic Information",
            {
                "fields": (
                    "name",
                    "public_email",
                    "contact_number_1",
                    "contact_number_2",
                    "contact_number_3",
                    "year_founded",
                    "registration_status",
                    "year_formally_registered",
                    "country_of_registration",
                )
            },
        ),
        (
            "Step 2 - Online Presence",
            {
                "fields": (
                    "website",
                    "twitter",
                    "facebook",
                    "whatsapp",
                    "linkedin",
                    "instagram",
                    "tiktok",
                )
            },
        ),
        (
            "Step 3 - Classification",
            {
                "fields": (
                    "org_type",
                    "county",
                    "sub_county",
                    "funding_source",
                    "is_youth_org",
                    "youth_type",
                    "is_disability_org",
                    "is_women_led",
                    "areas_of_intervention",
                )
            },
        ),
        (
            "Step 4 - Mental Health Focus",
            {
                "fields": (
                    "mh_focus_areas",
                    "mh_service_categories",
                )
            },
        ),
        (
            "Step 5 - Achievements and Advertising",
            {
                "fields": (
                    "objectives",
                    "mh_funding_used_kes",
                    "advertise_tier",
                )
            },
        ),
        (
            "Map Coordinates",
            {
                "fields": (
                    "latitude",
                    "longitude",
                )
            },
        ),
        (
            "Review Workflow",
            {
                "fields": (
                    "status",
                    "rejection_reason",
                    "reviewed_at",
                    "reviewed_by",
                )
            },
        ),
        (
            "Documents",
            {
                "fields": (
                    "registration_certificate",
                )
            },
        ),
        ("Timestamps", {"fields": ("submitted_at", "updated_at")}),
    )

    def save_model(self, request, obj, form, change):
        """Override save_model to send email on status change"""
        
        # Check if this is an update (not a new object)
        if change and obj.pk:
            # Get the original object from database
            original = Facility.objects.get(pk=obj.pk)
            original_status = original.status
            new_status = obj.status
            
            # If status has changed
            if original_status != new_status:
                obj.reviewed_by = request.user
                # Save the object first
                super().save_model(request, obj, form, change)
                
                # Send email notification
                if new_status in ['approved', 'rejected']:
                    email_sent = send_facility_status_email(obj, new_status)
                    
                    if email_sent:
                        messages.success(
                            request,
                            f'Facility status updated to "{new_status}" and notification email sent.'
                        )
                    else:
                        messages.warning(
                            request,
                            f'Facility status updated to "{new_status}" but email notification failed.'
                        )
                return
        
        # Default save for new objects or status didn't change
        super().save_model(request, obj, form, change)



@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):

    list_display = (
        'reporting_organisation',
        'sub_county',
        'level_of_implementation',
        'numbers_reached',
        'period',
        'created_at'
    )

    list_filter = (
        'level_of_implementation',
        'sub_county',
        'created_at'
    )

    search_fields = (
        'reporting_organisation__org_name',
        'partner_name',
        'activity'
    )


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):

    list_display = (
        "organization",
        "name",
        "is_anonymous",
        "created_at"
    )

    list_filter = (
        "is_anonymous",
        "created_at"
    )

    search_fields = (
        "name",
        "email",
        "message"
    )
