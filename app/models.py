from django.db import models
import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


# ─────────────────────────────────────────────
#  CHOICES
# ─────────────────────────────────────────────

class RegistrationStatus(models.TextChoices):
    PENDING  = 'pending',  'Pending Review'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'


class AdvertiseTier(models.TextChoices):
    NONE    = 'none',    'Free (no ad)'
    BASIC   = 'basic',   'Basic – $25/mo'
    PREMIUM = 'premium', 'Premium – $60/mo'


class OrgType(models.TextChoices):
    INTL_NGO = 'International NGO',   'International NGO'
    LOCAL_NGO = 'Local NGO', 'Local NGO'
    PUBLIC   = 'Public',    'Public'
    PRIVATE  = 'Private',   'Private'
    CBO      = 'Community Based Org',        'Community-Based Org'
    COALITION = 'Coalition', 'Coalition'
    NETWORK  = 'Network',    'Network'
    OTHER    = 'Other',      'Other'


class FundingSource(models.TextChoices):
    LOCAL   = 'Local',   'Local (≥50%)'
    FOREIGN = 'Foreign', 'Foreign (≥50%)'
    MIXED   = 'Mixed',   'Mixed'


class YouthType(models.TextChoices):
    LED     = 'Youth-led',     'Youth-led'
    SERVING = 'Youth-serving', 'Youth-serving'
    BOTH    = 'Youth-led & Youth-serving',    'Youth-led & Youth-serving'


class MHFocusArea(models.TextChoices):
    PROMOTIVE      = 'promotive',      'Promotive & Preventive'
    CURATIVE       = 'curative',       'Curative'
    REHABILITATIVE = 'rehabilitative', 'Rehabilitative'


class MHServiceCategory(models.TextChoices):
    PSYCHOTHERAPY        = 'psychotherapy',        'Psychotherapy & Counseling'
    WELLNESS_CLINIC      = 'wellness_clinic',      'Mental Wellness Clinic'
    PSYCHIATRY           = 'psychiatry',           'Psychiatry'
    SCHOOL_MH            = 'school_mh',            'School Mental Health'
    COMMUNITY_MH         = 'community_mh',         'Community Mental Health'
    CHILD_ADOLESCENT     = 'child_adolescent',     'Child & Adolescent MH'
    MATERNAL_MH          = 'maternal_mh',          'Maternal MH'
    SCREENING            = 'screening',            'MH Screening & Assessments'
    MENS_MH              = 'mens_mh',              "Men's Mental Health"
    REHABILITATION       = 'rehabilitation',       'Rehabilitation'


class HearAboutUs(models.TextChoices):
    INTERNET   = 'internet',   'Internet Search'
    SOCIAL     = 'social',     'Social Media'
    DIRECT     = 'direct',     'Direct Mail or Physical Advertisement'
    REFERRAL   = 'referral',   'Referral'
    NEWS       = 'news',       'News Article'
    EVENT      = 'event',      'Event or Conference'
    OPDS       = 'opds',       'Our organization is already part of OPDs'
    FORUM      = 'forum',      'Heard about the platform during a forum'
    OTHER      = 'other',      'Other'


class AreaOfIntervention(models.TextChoices):
    HEALTH        = 'health',        'Health'
    MENTAL_HEALTH = 'mental_health', 'Mental Health'
    EDUCATION     = 'education',     'Education'
    ENVIRONMENT   = 'environment',   'Environment'
    CLIMATE       = 'climate',       'Climate Change'
    LIVELIHOODS   = 'livelihoods',   'Livelihoods'


# ─────────────────────────────────────────────
#  CUSTOM USER / ORGANIZATION ACCOUNT
#  (The "Register" form on the auth page)
# ─────────────────────────────────────────────

class OrganizationManager(BaseUserManager):
    def create_user(self, email, org_name, password=None, **extra):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, org_name=org_name, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, org_name, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        extra.setdefault('status', RegistrationStatus.APPROVED)
        return self.create_user(email, org_name, password, **extra)


class Organization(AbstractBaseUser, PermissionsMixin):
    """
    One account per organization.
    Corresponds to the Register form (auth page).
    """

    # ── Core identity ──
    org_name             = models.CharField('Name of Organization', max_length=255)
    email                = models.EmailField('Email Address', unique=True)

    # ── Contact details (from Register form) ──
    contact_person       = models.CharField('Contact Person', max_length=150)
    correspondence_phone = models.CharField('Correspondence Number', max_length=30)
    correspondence_email = models.EmailField('Correspondence Email')
    logo = models.ImageField('Organization Logo', upload_to='organization_logos/', null=True, blank=True)

    # ── Discovery ──
    hear_about_us        = models.CharField(
        'How did you hear about us?',
        max_length=20,
        choices=HearAboutUs.choices,
        default=HearAboutUs.REFERRAL,
    )
    hear_about_us_other  = models.CharField(
        'If Other, please specify',
        max_length=255,
        blank=True,
    )

    # ── IDL review status ──
    status               = models.CharField(
        max_length=10,
        choices=RegistrationStatus.choices,
        default=RegistrationStatus.PENDING,
        db_index=True,
    )
    rejection_reason     = models.TextField(blank=True)
    reviewed_at          = models.DateTimeField(null=True, blank=True)
    reviewed_by          = models.ForeignKey(
        'self',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_orgs',
    )

    # ── Timestamps ──
    date_joined          = models.DateTimeField(default=timezone.now)
    updated_at           = models.DateTimeField(auto_now=True)

    # ── Django auth flags ──
    is_active            = models.BooleanField(default=True)
    is_staff             = models.BooleanField(default=False)

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['org_name']

    objects = OrganizationManager()

    class Meta:
        verbose_name        = 'Organization'
        verbose_name_plural = 'Organizations'
        ordering            = ['-date_joined']

    def __str__(self):
        return f'{self.org_name} ({self.email})'

    @property
    def is_approved(self):
        return self.status == RegistrationStatus.APPROVED


# ─────────────────────────────────────────────
#  FACILITY
#  (The 5-step "Add a Facility" modal)
# ─────────────────────────────────────────────

class Facility(models.Model):
    """
    A mental health facility submitted by an Organization.
    Covers all 5 steps of the Add Facility modal.
    """

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='facilities',
    )

    # ────────────────────────────────────────
    #  STEP 1 — Basic Information
    # ────────────────────────────────────────

    name                   = models.CharField('Name of Organization', max_length=255)
    public_email           = models.EmailField('Public Contact Email')
    contact_number_1       = models.CharField('Contact Number 1', max_length=30)
    contact_number_2       = models.CharField('Contact Number 2', max_length=30, blank=True)
    contact_number_3       = models.CharField('Contact Number 3', max_length=30, blank=True)

    year_founded           = models.PositiveSmallIntegerField('Year Founded', null=True, blank=True)
    registration_status    = models.CharField('Registration Status', max_length=10,
        choices=[('Formal', 'Formal'), ('Informal', 'Informal')],
        blank=True,
    )
    year_formally_registered = models.PositiveSmallIntegerField(
        'Year Formally Registered', null=True, blank=True
    )
    country_of_registration = models.CharField(
        'Country of First Registration', max_length=100, default='Kenya'
    )

    # ────────────────────────────────────────
    #  STEP 2 — Online Presence
    # ────────────────────────────────────────

    website    = models.URLField(blank=True)
    twitter    = models.URLField('Twitter / X', blank=True)
    facebook   = models.URLField(blank=True)
    whatsapp   = models.URLField('WhatsApp Group', blank=True)
    linkedin   = models.URLField(blank=True)
    instagram  = models.URLField(blank=True)
    tiktok     = models.URLField(blank=True)

    # ────────────────────────────────────────
    #  STEP 3 — Classification
    # ────────────────────────────────────────

    org_type      = models.CharField(
        'Type of Organization',
        max_length=50,
        choices=OrgType.choices,
        blank=True,
    )
    county        = models.CharField('County', max_length=100)
    sub_county    = models.CharField('Sub-County', max_length=100)
    funding_source = models.CharField(
        'Main Funding Sources',
        max_length=10,
        choices=FundingSource.choices,
        blank=True,
    )

    # Yes/No flags
    is_youth_org        = models.BooleanField('Youth Organization?', null=True)
    youth_type          = models.CharField(
        'Youth Type', max_length=60,
        choices=YouthType.choices,
        blank=True, null=True,
    )
    is_disability_org   = models.BooleanField('Organization for Persons with Disabilities?', null=True)
    is_women_led       = models.BooleanField('Women-led?', null=True)

    # Many-to-many style via JSON / separate table — stored as comma-joined choices
    # Using a simple TextField with choices reference; swap for ManyToManyField if preferred
    areas_of_intervention = models.JSONField(
        'Areas of Intervention',
        default=list,
        help_text='List of AreaOfIntervention values e.g. ["health", "mental_health"]',
    )

    # ────────────────────────────────────────
    #  STEP 4 — MH Focus
    # ────────────────────────────────────────

    mh_focus_areas = models.JSONField(
        'MH Focus Areas',
        default=list,
        help_text='List of MHFocusArea values e.g. ["promotive", "curative"]',
    )
    mh_service_categories = models.JSONField(
        'MH Service Categories',
        default=list,
        help_text='List of MHServiceCategory values e.g. ["psychotherapy", "psychiatry"]',
    )

    # ────────────────────────────────────────
    #  STEP 5 — Achievements & Advertising
    # ────────────────────────────────────────

    objectives       = models.TextField('Achievements objectives and Key impact areas', blank=True)
    mh_funding_used_kes = models.DecimalField(
        'MH Funding Used (KES)',
        max_digits=14, decimal_places=2,
        null=True, blank=True,
    )
    advertise_tier     = models.CharField(
        'Advertise on Platform',
        max_length=10,
        choices=AdvertiseTier.choices,
        default=AdvertiseTier.NONE,
    )

    # ────────────────────────────────────────
    #  LOCATION — Latitude & Longitude
    #  (for the Leaflet map)
    # ────────────────────────────────────────

    latitude  = models.DecimalField(
        'Latitude',
        max_digits=9, decimal_places=6,
        null=True, blank=True,
        help_text='e.g. -1.292100 for Nairobi',
    )
    longitude = models.DecimalField(
        'Longitude',
        max_digits=9, decimal_places=6,
        null=True, blank=True,
        help_text='e.g. 36.821900 for Nairobi',
    )

    street_address = models.CharField(
    'Street Address',
    max_length=255,
    blank=True
    )

    # ────────────────────────────────────────
    #  IDL REVIEW
    # ────────────────────────────────────────

    status           = models.CharField(
        max_length=10,
        choices=RegistrationStatus.choices,
        default=RegistrationStatus.PENDING,
        db_index=True,
    )
    rejection_reason = models.TextField(blank=True)
    reviewed_at      = models.DateTimeField(null=True, blank=True)
    reviewed_by      = models.ForeignKey(
        Organization,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_facilities',
    )

    # ────────────────────────────────────────
    #  SUPPORTING DOCUMENTS (for updates/resubmissions)
    # ────────────────────────────────────────

    registration_certificate = models.FileField(
        'Registration Certificate',
        upload_to='facility_docs/',
        null=True, blank=True,
    )

    # ────────────────────────────────────────
    #  TIMESTAMPS
    # ────────────────────────────────────────

    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Facility'
        verbose_name_plural = 'Facilities'
        ordering            = ['-submitted_at']

    def __str__(self):
        return f'{self.name} — {self.county} [{self.status}]'

    @property
    def is_approved(self):
        return self.status == RegistrationStatus.APPROVED

    @property
    def is_featured(self):
        """True if org is paying to advertise (Basic or Premium)."""
        return self.advertise_tier in (AdvertiseTier.BASIC, AdvertiseTier.PREMIUM)

    @property
    def coordinates(self):
        """Returns (lat, lng) tuple or None if not set."""
        if self.latitude is not None and self.longitude is not None:
            return (float(self.latitude), float(self.longitude))
        return None




class Resources(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('draft', 'Draft'),
        ('archived', 'Archived'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    notice_file = models.FileField(upload_to='resources/', help_text="Upload a PDF file.")
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Resource"
        verbose_name_plural = "Resources"

    def __str__(self):
        return self.title
    

class Activity(models.Model):

    LEVEL_CHOICES = [
        ('planned', 'Planned'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
    ]

    reporting_organisation = models.ForeignKey(
        "Organization",
        on_delete=models.CASCADE,
        related_name="activities"
    )

    partner_name = models.CharField(max_length=255, blank=True, null=True)
    sub_county = models.CharField(max_length=255)

    strategic_objective = models.CharField(max_length=255)
    strategic_area = models.CharField(max_length=255)
    strategic_action = models.CharField(max_length=255)

    activity = models.TextField()

    target_population = models.CharField(max_length=255)
    numbers_reached = models.IntegerField(default=0)

    level_of_implementation = models.CharField(
        max_length=50,
        choices=LEVEL_CHOICES
    )

    period = models.CharField(max_length=255)

    cost = models.DecimalField(max_digits=12, decimal_places=2)
    overall_cost = models.DecimalField(max_digits=12, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        ordering = ['-created_at']
        verbose_name = "Activity"
        verbose_name_plural = "Activities"

    def __str__(self):
        return self.reporting_organisation.org_name



# models.py

import uuid
from django.db import models


class Feedback(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    organization = models.ForeignKey(
        "Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    message = models.TextField()

    is_anonymous = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Feedback - {self.created_at}"