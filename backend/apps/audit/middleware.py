from django.utils.deprecation import MiddlewareMixin
from .models import AuditLog

class AuditLogMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        # We selectively record state changes and logins
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE'] and response.status_code in [200, 201]:
            path = request.path
            user = getattr(request, 'user', None)
            if user and user.is_authenticated:
                ip = request.META.get('REMOTE_ADDR')
                h_name = user.hospital.hospital_name if user.hospital else 'Platform'
                if '/api/referrals/' in path and '/transition/' in path:
                    AuditLog.objects.create(
                        user=user,
                        user_email=user.email,
                        hospital=user.hospital,
                        hospital_name=h_name,
                        action='REFERRAL_TRANSITION',
                        resource='Referral',
                        ip_address=ip,
                        details=f"Referral status transition via API"
                    )
        return response
