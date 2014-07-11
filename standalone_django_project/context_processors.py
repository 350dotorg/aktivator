from django.conf import settings

def globals(request):
    return {
        'SITE_NAME': settings.SITE_NAME,
        'SITE_DOMAIN': settings.SITE_DOMAIN,
        'ACTIONKIT_URL': settings.ACTIONKIT_API_HOST,
        }
