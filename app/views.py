from django.http import JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from .forms import OrganizationLoginForm, OrganizationRegistrationForm
from .models import AdvertiseTier, Facility, Feedback, RegistrationStatus, Resources
from .models import Facility, Organization, Activity
from django.views.decorators.http import require_http_methods
from django.contrib.auth.hashers import check_password, make_password
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Sum
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


# ─────────────────────────────────────────────
#  REGISTER
# ─────────────────────────────────────────────
from threading import Thread

def send_registration_emails(org, request):
    context = {
        "organization": org,
        "facility": org,
        "admin_url": request.build_absolute_uri("/admin/")
    }

    # User email
    user_html = render_to_string(
        "app/emails/facility_created_user.html",
        context
    )

    user_email = EmailMultiAlternatives(
        subject="ORGANIZATION REGISTRATION SUBMITTED",
        body="",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[org.email],
    )
    user_email.attach_alternative(user_html, "text/html")
    user_email.send()

    # Admin email
    admin_html = render_to_string(
        "app/emails/facility_created_admin.html",
        context
    )

    admin_email = EmailMultiAlternatives(
        subject=f"NEW ORGANIZATION REGISTRATION - {org.org_name}",
        body="",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=["kimonesmuske@gmail.com"],
    )
    admin_email.attach_alternative(admin_html, "text/html")
    admin_email.send()


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    login_data = {"email": ""}

    if request.method == 'POST':
        registration_form = OrganizationRegistrationForm(request.POST, request.FILES)
        if registration_form.is_valid():
            org = registration_form.save(commit=False)
            org.email = org.email.lower()
            org.correspondence_email = org.correspondence_email.lower()
            org.status = RegistrationStatus.PENDING
            org.set_password(registration_form.cleaned_data["password"])
            org.save()

            Thread(
                target=send_registration_emails,
                args=(org, request),
                daemon=True
            ).start()

            messages.success(
                request,
                f"Thank you, {org.org_name}! Your registration has been submitted. "
                "The IDL team will review your application and notify you by email.",
            )
            return redirect('login')

        messages.error(request, "Please correct the registration errors below.")
        return render(
            request,
            'app/auth.html',
            {
                'active_tab': 'register',
                'registration_form': registration_form,
                'login_data': login_data,
            },
        )

    return render(
        request,
        'app/auth.html',
        {
            'active_tab': 'register',
            'registration_form': OrganizationRegistrationForm(),
            'login_data': login_data,
        },
    )


# ─────────────────────────────────────────────
#  LOGIN
# ─────────────────────────────────────────────

def login_view(request):
    organizations = Organization.objects.filter(status=RegistrationStatus.APPROVED, is_superuser=False).count()
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = OrganizationLoginForm(request.POST)
        if form.is_valid():
            login(request, form.cleaned_data["user"])
            if not form.cleaned_data.get("remember_me"):
                request.session.set_expiry(0)
            return redirect('dashboard')

        messages.error(request, "Please check your login details and try again.")
        return render(
            request,
            'app/auth.html',
            {
                'active_tab': 'login',
                'login_form': form,
                'login_data': {'email': request.POST.get('email', '').strip().lower()},
                'registration_form': OrganizationRegistrationForm(),
                'organizations': organizations,
            },
        )

    login_form = OrganizationLoginForm()
    registration_form = OrganizationRegistrationForm()
    return render(
        request,
        'app/auth.html',
        {
            'active_tab': 'login',
            'login_form': login_form,
            'registration_form': registration_form,
            'login_data': {'email': ''},
            'organizations': organizations,
        },
    )


# ─────────────────────────────────────────────
#  LOGOUT
# ─────────────────────────────────────────────

@require_POST
def logout_view(request):
    logout(request)
    return redirect('login')


# ─────────────────────────────────────────────
#  DASHBOARD  (protected)
# ─────────────────────────────────────────────

def dashboard_view(request):
    all_facilities = Facility.objects.all()
    my_application = None
    my_facilities = None
    activity = None

    organizations = Organization.objects.filter(status=RegistrationStatus.APPROVED, is_superuser=False)
    if request.user.is_authenticated:
        
        my_application = Organization.objects.filter(
            email=request.user.email
        ).first()

        activity = Activity.objects.filter(reporting_organisation__email=request.user.email)

        if my_application:
            my_facilities = my_application.facilities.filter(status=RegistrationStatus.APPROVED).order_by('-submitted_at')

    context = {
        'total': all_facilities.count(),
        'approved_count': all_facilities.filter(status=RegistrationStatus.APPROVED).count(),
        'pending_count': all_facilities.filter(status=RegistrationStatus.PENDING).count(),
        'rejected_count': all_facilities.filter(status=RegistrationStatus.REJECTED).count(),
        'featured': Facility.objects.filter(
            status=RegistrationStatus.APPROVED,
            advertise_tier__in=[AdvertiseTier.BASIC, AdvertiseTier.PREMIUM]
        ).select_related('organization').order_by('-advertise_tier', 'name'),
        'my_application': my_application,
        'my_facilities': my_facilities,
        'open_add_facility': request.GET.get('open_add_facility') == '1',
        'organizations_count': organizations.count(),
        'organizations': organizations,
        "resources": Resources.objects.filter(status="active").order_by("-created_at"),
        "activities": activity,
        "total_reached": Activity.objects.aggregate(total=Sum("numbers_reached"))["total"] or 0,
        "total_mh_funding": Facility.objects.aggregate(total=Sum("mh_funding_used_kes"))["total"] or 0,
    }


    return render(request, 'app/dashboard.html', context)



@login_required
def add_facility(request):

    user = request.user

    # Get organization
    try:
        organization = request.user
    except Organization.DoesNotExist:
        messages.error(request, "You must create an organization first.")
        return redirect("dashboard")

    # Check approval
    if not organization.is_approved:
        messages.warning(
            request,
            "Your organization is pending approval. You cannot add a facility."
        )
        return redirect("dashboard")

    if request.method == "POST":

        # ─────────────────────────────
        # Step 3 & 4 (checkbox JSON fields)
        # ─────────────────────────────

        areas_of_intervention = request.POST.getlist("areas_of_intervention")
        mh_focus_areas = request.POST.getlist("mh_focus_areas")
        mh_service_categories = request.POST.getlist("mh_service_categories")

        facility = Facility.objects.create(

            organization=organization,

            # ─────────────────────────────
            # STEP 1
            # ─────────────────────────────

            name=request.POST.get("name"),
            public_email=request.POST.get("public_email"),
            contact_number_1=request.POST.get("contact_number_1"),
            contact_number_2=request.POST.get("contact_number_2"),
            contact_number_3=request.POST.get("contact_number_3"),
            year_founded=request.POST.get("year_founded"),
            registration_status=request.POST.get("registration_status"),
            year_formally_registered=request.POST.get("year_formally_registered"),
            country_of_registration=request.POST.get("country_of_registration"),

            # ─────────────────────────────
            # STEP 2
            # ─────────────────────────────

            website=request.POST.get("website"),
            twitter=request.POST.get("twitter"),
            facebook=request.POST.get("facebook"),
            whatsapp=request.POST.get("whatsapp"),
            linkedin=request.POST.get("linkedin"),
            instagram=request.POST.get("instagram"),
            tiktok=request.POST.get("tiktok"),

            # ─────────────────────────────
            # STEP 3
            # ─────────────────────────────

            org_type=request.POST.get("org_type"),
            county=request.POST.get("county"),
            sub_county=request.POST.get("sub_county"),
            funding_source=request.POST.get("funding_source"),

            is_youth_org=request.POST.get("is_youth_org") == "yes",
            youth_type=request.POST.get("youth_type"),
            is_disability_org=request.POST.get("is_disability_org") == "yes",
            is_women_led=request.POST.get("is_female_led") == "yes",

            # ─────────────────────────────
            # STEP 4
            # ─────────────────────────────

            mh_focus_areas=mh_focus_areas,
            mh_service_categories=mh_service_categories,

            # ─────────────────────────────
            # STEP 5
            # ─────────────────────────────

            objectives=request.POST.get("achievements"),
            mh_funding_used_kes=request.POST.get("mh_funding_used_kes"),
            advertise_tier=request.POST.get("advertise"),

            # ─────────────────────────────
            # Location
            # ─────────────────────────────

            latitude=request.POST.get("latitude"),
            longitude=request.POST.get("longitude"),
            street_address=request.POST.get("street_address"),

            # ─────────────────────────────
            # JSON
            # ─────────────────────────────

            areas_of_intervention=areas_of_intervention,

        )
        facility.save()

        messages.success(request, "Facility submitted successfully. Await approval.")
        return redirect("dashboard")

    return redirect("dashboard")



def facilities_map_data(request):
    org_type = request.GET.get("org_type")
    youth_type = request.GET.get("youth_type")
    funding_source = request.GET.get("funding_source")

    facilities = Facility.objects.filter(
        status="approved"
    )

    # Apply filters
    if org_type:
        facilities = facilities.filter(org_type=org_type)

    if youth_type:
        facilities = facilities.filter(youth_type=youth_type)

    if funding_source:
        facilities = facilities.filter(funding_source=funding_source)

    data = []

    for f in facilities:
        data.append({
            "name": f.name,
            "lat": float(f.latitude),   # convert to float
            "lng": float(f.longitude),
            "sub_county": f.sub_county,
            "county": f.county,
            "status": f.status,
            "type": f.org_type,
            "youth_type": f.is_youth_org,
            "funding_source": f.funding_source,
            "year_founded": f.year_founded,
            "public_email": f.public_email
        })

    return JsonResponse(data, safe=False)



def facility_filters(request):

    org_types = Facility.objects.values_list(
        "org_type", flat=True
    ).distinct()

    youth_types = Facility.objects.values_list(
        "youth_type", flat=True
    ).distinct()

    funding_sources = Facility.objects.values_list(
        "funding_source", flat=True
    ).distinct()

    return JsonResponse({
        "org_types": list(filter(None, org_types)),
        "youth_types": list(filter(None, youth_types)),
        "funding_sources": list(filter(None, funding_sources)),
    })


@require_http_methods(["POST"])
@csrf_exempt  # Only use this if you handle CSRF differently, see below
def update_profile(request):
    try:
        data = json.loads(request.body)
        user = request.user
        
        user.org_name = data.get('org_name', user.org_name)
        user.contact_person = data.get('contact_person', user.contact_person)
        user.email = data.get('email', user.email)
        user.correspondence_phone = data.get('correspondence_phone', user.correspondence_phone)
        user.save()
        
        return JsonResponse({'success': True, 'message': 'Profile updated'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@require_http_methods(["POST"])
@csrf_exempt
def change_password(request):
    try:
        data = json.loads(request.body)
        user = request.user
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        confirm_new_password = data.get('confirm_new_password')
        
        # Check if new password and confirm password match
        if new_password != confirm_new_password:
            return JsonResponse({'success': False, 'message': 'New passwords do not match'}, status=400)
        
        # Check if current password is correct
        if not check_password(current_password, user.password):
            return JsonResponse({'success': False, 'message': 'Current password is incorrect'}, status=400)
        
        # Check if new password is not empty
        if not new_password or len(new_password) < 8:
            return JsonResponse({'success': False, 'message': 'New password must be at least 8 characters long'}, status=400)
        
        user.password = make_password(new_password)
        user.save()
        
        return JsonResponse({'success': True, 'message': 'Password updated successfully'})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)



class FacilityEncoder(DjangoJSONEncoder):
    """Custom JSON encoder for Facility model"""
    def default(self, obj):
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return super().default(obj)


@login_required
def get_facility_data(request, facility_id):
    """
    Fetch a single facility's data for editing
    Returns JSON with all facility details
    """
    try:
        # Get the facility, ensuring the user owns it
        facility = get_object_or_404(
            Facility,
            id=facility_id,
            organization=request.user.organization if hasattr(request.user, 'organization') else request.user
        )
        
        facility_data = {
            'id': facility.id,
            'name': facility.name,
            'email': facility.public_email,
            'phone': facility.contact_number_1,
            'phone2': facility.contact_number_2 or '',
            'phone3': facility.contact_number_3 or '',
            'website': facility.website or '',
            'twitter': facility.twitter or '',
            'facebook': facility.facebook or '',
            'whatsapp': facility.whatsapp or '',
            'linkedin': facility.linkedin or '',
            'instagram': facility.instagram or '',
            'tiktok': facility.tiktok or '',
            'county': facility.county,
            'sub_county': facility.sub_county,
            'street_address': facility.street_address or '',
            'year_founded': facility.year_founded or '',
            'registration_status': facility.registration_status or '',
            'year_formally_registered': facility.year_formally_registered or '',
            'country_of_registration': facility.country_of_registration or 'Kenya',
            'org_type': facility.org_type or '',
            'is_youth_org': facility.is_youth_org,
            'youth_type': facility.youth_type or '',
            'is_disability_org': facility.is_disability_org,
            'is_women_led': facility.is_women_led,
            'areas_of_intervention': facility.areas_of_intervention or [],
            'mh_focus_areas': facility.mh_focus_areas or [],
            'mh_service_categories': facility.mh_service_categories or [],
            'objectives': facility.objectives or '',
            'mh_funding_used_kes': str(facility.mh_funding_used_kes or 0),
            'latitude': str(facility.latitude or ''),
            'longitude': str(facility.longitude or ''),
            'status': facility.status,
            'status_label': facility.get_status_display(),
            'rejection_reason': facility.rejection_reason or '',
            'reviewed_at': facility.reviewed_at.isoformat() if facility.reviewed_at else None,
            'submitted_at': facility.submitted_at.isoformat(),
            'updated_at': facility.updated_at.isoformat(),
            'location': f"{facility.county}, {facility.sub_county}",
            'type': facility.org_type,
            'note': get_facility_note(facility),
        }
        
        return JsonResponse({
            'success': True,
            'data': facility_data
        })
        
    except Facility.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Facility not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def update_facility(request, facility_id):
    """
    Update facility details
    """
    try:
        # Get the facility
        facility = get_object_or_404(
            Facility,
            id=facility_id,
            organization=request.user.organization if hasattr(request.user, 'organization') else request.user
        )
        
        # Parse request data
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = request.POST
        
        # Update basic information
        if 'name' in data:
            facility.name = data['name']
        if 'email' in data:
            facility.public_email = data['email']
        if 'phone' in data:
            facility.contact_number_1 = data['phone']
        if 'phone2' in data:
            facility.contact_number_2 = data.get('phone2', '')
        if 'phone3' in data:
            facility.contact_number_3 = data.get('phone3', '')
        
        # Update online presence
        if 'website' in data:
            facility.website = data.get('website', '')
        if 'twitter' in data:
            facility.twitter = data.get('twitter', '')
        if 'facebook' in data:
            facility.facebook = data.get('facebook', '')
        if 'whatsapp' in data:
            facility.whatsapp = data.get('whatsapp', '')
        if 'linkedin' in data:
            facility.linkedin = data.get('linkedin', '')
        if 'instagram' in data:
            facility.instagram = data.get('instagram', '')
        if 'tiktok' in data:
            facility.tiktok = data.get('tiktok', '')
        
        # Update location
        if 'county' in data:
            facility.county = data['county']
        if 'sub_county' in data:
            facility.sub_county = data['sub_county']
        if 'street_address' in data:
            facility.street_address = data.get('street_address', '')
        
        # Update classification
        if 'year_founded' in data and data['year_founded']:
            facility.year_founded = int(data['year_founded'])
        if 'registration_status' in data:
            facility.registration_status = data.get('registration_status', '')
        if 'year_formally_registered' in data and data['year_formally_registered']:
            facility.year_formally_registered = int(data['year_formally_registered'])
        if 'country_of_registration' in data:
            facility.country_of_registration = data.get('country_of_registration', 'Kenya')
        if 'org_type' in data:
            facility.org_type = data.get('org_type', '')
        if 'is_youth_org' in data:
            facility.is_youth_org = data['is_youth_org'] in [True, 'true', 'True', 1, '1']
        if 'youth_type' in data:
            facility.youth_type = data.get('youth_type', '')
        if 'is_disability_org' in data:
            facility.is_disability_org = data['is_disability_org'] in [True, 'true', 'True', 1, '1']
        if 'is_women_led' in data:
            facility.is_women_led = data['is_women_led'] in [True, 'true', 'True', 1, '1']
        
        # Update MH focus areas
        if 'mh_service_categories' in data:
            facility.mh_service_categories = data['mh_service_categories'] if isinstance(data['mh_service_categories'], list) else []
        if 'mh_focus_areas' in data:
            facility.mh_focus_areas = data['mh_focus_areas'] if isinstance(data['mh_focus_areas'], list) else []
        if 'areas_of_intervention' in data:
            facility.areas_of_intervention = data['areas_of_intervention'] if isinstance(data['areas_of_intervention'], list) else []
        
        # Update achievements
        if 'objectives' in data:
            facility.objectives = data.get('objectives', '')
        if 'mh_funding_used_kes' in data and data['mh_funding_used_kes']:
            facility.mh_funding_used_kes = float(data['mh_funding_used_kes'])
        
        # Update coordinates if provided
        if 'latitude' in data and data['latitude']:
            facility.latitude = float(data['latitude'])
        if 'longitude' in data and data['longitude']:
            facility.longitude = float(data['longitude'])
        
        # Handle file uploads
        if 'registration_certificate' in request.FILES:
            facility.registration_certificate = request.FILES['registration_certificate']
        
        # Save the facility
        facility.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Facility updated successfully',
            'facility': {
                'id': facility.id,
                'name': facility.name,
                'status': facility.status,
            }
        })
        
    except Facility.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Facility not found'
        }, status=404)
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': f'Invalid data format: {str(e)}'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def get_facility_note(facility):
    """
    Generate the appropriate note/message based on facility status
    """
    if facility.status == 'approved':
        return {
            'type': 'success',
            'title': f'Approved by IDL — {facility.reviewed_at.strftime("%d %b %Y") if facility.reviewed_at else ""}',
            'body': 'Your facility is live on the public dashboard. Updates will be re-reviewed by IDL before going live.',
        }
    elif facility.status == 'pending':
        return {
            'type': 'info',
            'title': 'Currently Under Review',
            'body': 'Your submission is being reviewed. You can update details now — changes will be included in the ongoing review.',
        }
    elif facility.status == 'rejected':
        return {
            'type': 'error',
            'title': f'Rejected by IDL — {facility.reviewed_at.strftime("%d %b %Y") if facility.reviewed_at else ""}',
            'body': f'{facility.rejection_reason or "The MH focus areas do not match your described services."} Fix the issues and resubmit.',
        }
    else:
        return {
            'type': 'info',
            'title': 'Status Update',
            'body': 'Your facility submission is being processed.',
        }


@login_required
def list_my_facilities(request):
    """
    Get list of all facilities for the logged-in organization
    Used to populate the facilities list on the page
    """
    try:
        # Get facilities for the current user's organization
        if hasattr(request.user, 'organization'):
            organization = request.user.organization
        else:
            organization = request.user
        
        facilities = Facility.objects.filter(organization=organization).order_by('-submitted_at')
        
        facilities_data = []
        for facility in facilities:
            facilities_data.append({
                'id': facility.id,
                'name': facility.name,
                'county': facility.county,
                'org_type': facility.org_type,
                'status': facility.status,
                'status_label': facility.get_status_display(),
                'submitted_at': facility.submitted_at.strftime('%d %b %Y'),
                'updated_at': facility.updated_at.strftime('%d %b %Y'),
                'reviewed_at': facility.reviewed_at.strftime('%d %b %Y') if facility.reviewed_at else None,
                'is_approved': facility.is_approved,
                'mh_service_categories': facility.mh_service_categories,
                'rejection_reason': facility.rejection_reason,
            })
        
        return JsonResponse({
            'success': True,
            'facilities': facilities_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
    



def add_activity(request):

    if request.method == "POST":

        try:
            organization = Organization.objects.get(email=request.user.email)

            Activity.objects.create(
                reporting_organisation=organization,
                partner_name=request.POST.get("partner_name"),
                sub_county=request.POST.get("sub_county"),
                strategic_objective=request.POST.get("strategic_objective"),
                strategic_area=request.POST.get("strategic_area"),
                strategic_action=request.POST.get("strategic_action"),
                activity=request.POST.get("activity"),
                target_population=request.POST.get("target_population"),
                numbers_reached=request.POST.get("numbers_reached"),
                level_of_implementation=request.POST.get("level_of_implementation"),
                period=request.POST.get("period"),
                cost=request.POST.get("cost"),
                overall_cost=request.POST.get("overall_cost"),
            )

            messages.success(request, "Activity added successfully ✅")

        except Exception as e:
            messages.error(request, "Failed to add activity ❌")

        return redirect("dashboard")



def submit_feedback(request):

    if request.method == "POST":

        organization = None

        if request.user.is_authenticated:
            try:
                organization = Organization.objects.get(
                    email=request.user.email
                )
            except:
                pass

        Feedback.objects.create(
            organization=organization,
            name=request.POST.get("name"),
            email=request.POST.get("email"),
            message=request.POST.get("message"),
            is_anonymous=request.POST.get("anonymous") == "on"
        )

        messages.success(request, "Thank you for your feedback")

        return redirect(request.META.get('HTTP_REFERER'))
