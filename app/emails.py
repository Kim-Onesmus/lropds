import logging
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

logger = logging.getLogger(__name__)


def send_organization_status_email(organization, new_status):
    """
    Send email notification when organization status is updated.
    
    Args:
        organization: Organization instance
        new_status: The new status (e.g., 'approved', 'rejected')
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    
    logger.info(f"Starting email send for organization {organization.id} with status {new_status}")
    
    # Verify settings are configured
    if not settings.DEFAULT_FROM_EMAIL:
        logger.error("DEFAULT_FROM_EMAIL is not configured in settings")
        return False
    
    # Determine email recipients
    recipients = []
    if organization.email:
        recipients.append(organization.email)
    if organization.correspondence_email and organization.correspondence_email != organization.email:
        recipients.append(organization.correspondence_email)
    
    if not recipients:
        logger.error(f"No email recipients found for organization {organization.id}")
        return False
    
    logger.info(f"Email recipients: {recipients}")
    
    # Email subject and context
    subject_map = {
        'approved': 'Your Organization Has Been Approved',
        'rejected': 'Your Organization Application Status',
    }
    
    template_map = {
        'approved': 'app/emails/organization_approved.html',
        'rejected': 'app/emails/organization_rejected.html',
    }
    
    subject = subject_map.get(new_status, 'Your Organization Status Has Been Updated')
    template = template_map.get(new_status, 'app/emails/organization_status_update.html')
    
    logger.info(f"Using subject: {subject}, template: {template}")
    
    contact_email = getattr(settings, 'CONTACT_EMAIL', 'support@example.com')
    logger.info(f"Contact email: {contact_email}")
    
    context = {
        'organization': organization,
        'status': new_status,
        'rejection_reason': organization.rejection_reason if new_status == 'rejected' else None,
        'contact_email': contact_email,
    }
    
    try:
        # Render HTML email
        logger.debug(f"Rendering template: {template}")
        html_message = render_to_string(template, context)
        logger.debug(f"Template rendered successfully, size: {len(html_message)} bytes")
        
        # Send email
        logger.info(f"Sending email from {settings.DEFAULT_FROM_EMAIL} to {recipients}")
        send_mail(
            subject=subject,
            message=f"Your organization status has been updated to {new_status}.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"✓ Email sent successfully to {recipients} for organization {organization.id}")
        return True
        
    except FileNotFoundError as e:
        logger.error(f"✗ Template not found: {str(e)}")
        logger.error(f"  Tried to load: {template}")
        logger.error(f"  Make sure templates exist at: yourapp/templates/{template}")
        return False
        
    except Exception as e:
        logger.error(f"✗ Error sending email: {type(e).__name__}: {str(e)}")
        logger.exception("Full exception details:")
        return False


def send_facility_status_email(facility, new_status):
    """
    Send email notification when facility status is updated.
    
    Args:
        facility: Facility instance
        new_status: The new status (e.g., 'approved', 'rejected')
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    
    logger.info(f"Starting email send for facility {facility.id} with status {new_status}")
    
    # Verify settings are configured
    if not settings.DEFAULT_FROM_EMAIL:
        logger.error("DEFAULT_FROM_EMAIL is not configured in settings")
        return False
    
    # Determine email recipients
    recipients = []
    organization = facility.organization
    
    if organization.email:
        recipients.append(organization.email)
    if organization.correspondence_email and organization.correspondence_email != organization.email:
        recipients.append(organization.correspondence_email)
    
    if facility.public_email and facility.public_email not in recipients:
        recipients.append(facility.public_email)
    
    if not recipients:
        logger.error(f"No email recipients found for facility {facility.id}")
        return False
    
    logger.info(f"Email recipients: {recipients}")
    
    # Email subject and context
    subject_map = {
        'approved': f'Facility "{facility.name}" Has Been Approved',
        'rejected': f'Facility "{facility.name}" Application Status',
    }
    
    template_map = {
        'approved': 'app/emails/facility_approved.html',
        'rejected': 'app/emails/facility_rejected.html',
    }
    
    subject = subject_map.get(new_status, f'Facility "{facility.name}" Status Has Been Updated')
    template = template_map.get(new_status, 'app/emails/facility_status_update.html')
    
    logger.info(f"Using subject: {subject}, template: {template}")
    
    contact_email = getattr(settings, 'CONTACT_EMAIL', 'support@example.com')
    logger.info(f"Contact email: {contact_email}")
    
    context = {
        'facility': facility,
        'organization': organization,
        'status': new_status,
        'rejection_reason': facility.rejection_reason if new_status == 'rejected' else None,
        'contact_email': contact_email,
    }
    
    try:
        # Render HTML email
        logger.debug(f"Rendering template: {template}")
        html_message = render_to_string(template, context)
        logger.debug(f"Template rendered successfully, size: {len(html_message)} bytes")
        
        # Send email
        logger.info(f"Sending email from {settings.DEFAULT_FROM_EMAIL} to {recipients}")
        send_mail(
            subject=subject,
            message=f"Facility status has been updated to {new_status}.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"✓ Email sent successfully to {recipients} for facility {facility.id}")
        return True
        
    except FileNotFoundError as e:
        logger.error(f"✗ Template not found: {str(e)}")
        logger.error(f"  Tried to load: {template}")
        logger.error(f"  Make sure templates exist at: yourapp/templates/{template}")
        return False
        
    except Exception as e:
        logger.error(f"✗ Error sending email: {type(e).__name__}: {str(e)}")
        logger.exception("Full exception details:")
        return False