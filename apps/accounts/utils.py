from django.core.mail import send_mail
from django.conf import settings


def send_verification_email(email, code):
    """
    Send verification code to user's email.
    
    Args:
        email: User's email address
        code: 4-digit verification code
    """
    subject = 'Email Verification Code'
    message = f'''
Hello,

Your verification code is: {code}

This code will expire in 5 minutes.

If you didn't request this code, please ignore this email.

Best regards,
Personal Finance Team
    '''
    
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [email]
    
    send_mail(
        subject,
        message,
        from_email,
        recipient_list,
        fail_silently=False,
    )