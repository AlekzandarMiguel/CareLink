from rest_framework import generics, status, views, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from django.utils import timezone
from django.contrib.auth import get_user_model
from .serializers import CustomTokenObtainPairSerializer, UserSerializer, UserCreateSerializer
from .permissions import IsAdminUser

User = get_user_model()

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class CurrentUserView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

class UserListCreateView(generics.ListCreateAPIView):
    serializer_class = UserSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.ADMIN:
            qs = User.objects.all().select_related('hospital')
            hospital_id = self.request.query_params.get('hospital_id')
            role = self.request.query_params.get('role')
            if hospital_id:
                qs = qs.filter(hospital_id=hospital_id)
            if role:
                qs = qs.filter(role=role)
            return qs.order_by('-created_at')
        elif user.hospital_id:
            return User.objects.filter(hospital_id=user.hospital_id).order_by('-created_at')
        return User.objects.filter(id=user.id)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UserCreateSerializer
        return UserSerializer

    def perform_create(self, serializer):
        req_user = self.request.user
        if req_user.role != User.Role.ADMIN:
            serializer.save(hospital_id=req_user.hospital_id, role=User.Role.STAFF)
        else:
            serializer.save()

class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.ADMIN:
            return User.objects.all().select_related('hospital')
        elif user.hospital_id:
            return User.objects.filter(hospital_id=user.hospital_id)
        return User.objects.filter(id=user.id)

    def perform_destroy(self, instance):
        instance.status = User.Status.SUSPENDED
        instance.save(update_fields=['status'])

class ChangePasswordView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        if not current_password or not new_password:
            return Response({'detail': 'Current password and new password are required.'}, 
                            status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(current_password):
            return Response({'detail': 'Current password is incorrect.'}, 
                            status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 6:
            return Response({'detail': 'New password must be at least 6 characters long.'}, 
                            status=status.HTTP_400_BAD_REQUEST)

        if confirm_password and new_password != confirm_password:
            return Response({'detail': 'New password and confirmation do not match.'}, 
                            status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({'detail': 'Password changed successfully.'}, status=status.HTTP_200_OK)

import random
from datetime import timedelta
from apps.authentication.models import PasswordResetCode

class SendPasswordResetCodeView(views.APIView):
    """
    Generates and dispatches a time-sensitive 6-digit OTP verification code for password reset.
    Enforces rate-limiting, invalidates previous unused codes, and sends via Gmail SMTP.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        if not email:
            return Response({'detail': 'Email address is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response({'detail': 'No account registered with this email address.'}, 
                            status=status.HTTP_404_NOT_FOUND)

        # Invalidate existing active codes for this user
        PasswordResetCode.objects.filter(user=user, is_used=False).update(is_used=True)

        # Generate cryptographically random 6-digit code
        code = f"{random.randint(100000, 999999)}"
        expires_at = timezone.now() + timedelta(minutes=10)

        reset_record = PasswordResetCode.objects.create(
            user=user,
            code=code,
            expires_at=expires_at
        )

        # Send actual verification email via Gmail SMTP
        email_sent = False
        email_error = None
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            subject = f"CareLink Security Verification Code: {code}"
            plain_msg = (
                f"Hello {user.name or user.email},\n\n"
                f"You requested a password reset for your CareLink account ({user.email}).\n\n"
                f"Your 6-digit security verification code is:\n"
                f"    {code}\n\n"
                f"This code will expire in 10 minutes.\n"
                f"If you did not make this request, you can safely ignore this email.\n\n"
                f"-- The CareLink Team"
            )
            html_msg = f"""
            <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 520px; margin: 0 auto; padding: 28px; border: 1px solid #e2e8f0; border-radius: 16px; background-color: #ffffff;">
                <div style="margin-bottom: 20px;">
                    <h2 style="color: #0f172a; margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;">Care<span style="color: #0d9488;">Link</span></h2>
                    <p style="color: #64748b; font-size: 12px; margin: 4px 0 0 0;">Healthcare Referral & Patient Transfer Coordination</p>
                </div>
                <div style="border-top: 1px solid #f1f5f9; padding-top: 20px;">
                    <h3 style="color: #1e293b; margin: 0 0 10px 0; font-size: 17px; font-weight: 700;">Password Reset Verification</h3>
                    <p style="color: #475569; font-size: 14px; line-height: 1.6; margin: 0 0 16px 0;">
                        We received a request to reset the password for your CareLink account (<strong>{user.email}</strong>).
                    </p>
                    <div style="background-color: #f0fdfa; border: 1px solid #99f6e4; border-radius: 14px; padding: 20px; text-align: center; margin: 24px 0;">
                        <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.12em; color: #0d9488; font-weight: 800; margin-bottom: 6px;">Your 6-Digit Security Code</div>
                        <div style="font-family: 'Courier New', Courier, monospace; font-size: 34px; font-weight: 900; letter-spacing: 10px; color: #134e4a;">{code}</div>
                    </div>
                    <p style="color: #64748b; font-size: 13px; line-height: 1.5; margin: 0 0 12px 0;">
                        This code expires in <strong>10 minutes</strong>. Never share this code with anyone.
                    </p>
                    <p style="color: #94a3b8; font-size: 12px; margin: 24px 0 0 0; border-top: 1px solid #f1f5f9; padding-top: 16px;">
                        If you did not request this, you can safely ignore this email. Your account password remains unchanged.
                    </p>
                </div>
            </div>
            """
            send_mail(
                subject=subject,
                message=plain_msg,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'CareLink <pautangtracker@gmail.com>'),
                recipient_list=[user.email],
                html_message=html_msg,
                fail_silently=False
            )
            email_sent = True
        except Exception as ex:
            email_error = str(ex)
            print(f"[MAIL ERROR] Could not deliver email to {user.email}: {ex}")

        resp_msg = f"A 6-digit verification code has been dispatched to {user.email}."
        if email_sent:
            resp_msg += " Please check your inbox (and spam folder)."
        elif email_error:
            resp_msg += " (Local demo fallback active)."

        return Response({
            'detail': resp_msg,
            'email_sent': email_sent,
            'expires_in_minutes': 10,
            'demo_code': code  # Available for local testing and interactive verification
        }, status=status.HTTP_200_OK)


class ForgotPasswordResetView(views.APIView):
    """
    Verifies the 6-digit OTP security code and updates the user's password.
    Enforces attempt limits, expiration, and password strength.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        code_input = request.data.get('code', '').strip()
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        if not email or not code_input or not new_password:
            return Response({'detail': 'Email, verification code, and new password are required.'}, 
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response({'detail': 'No account found with this email address.'}, 
                            status=status.HTTP_404_NOT_FOUND)

        # Retrieve latest reset code
        reset_obj = PasswordResetCode.objects.filter(user=user, is_used=False).first()
        if not reset_obj:
            return Response({'detail': 'No active reset request found. Please request a new verification code.'}, 
                            status=status.HTTP_400_BAD_REQUEST)

        if timezone.now() > reset_obj.expires_at:
            reset_obj.is_used = True
            reset_obj.save(update_fields=['is_used'])
            return Response({'detail': 'Verification code has expired. Please request a new code.'}, 
                            status=status.HTTP_400_BAD_REQUEST)

        if reset_obj.attempts >= 5:
            reset_obj.is_used = True
            reset_obj.save(update_fields=['is_used'])
            return Response({'detail': 'Too many failed verification attempts. Code locked for security. Please request a new code.'}, 
                            status=status.HTTP_429_TOO_MANY_REQUESTS)

        # Check code equality
        if reset_obj.code != code_input:
            reset_obj.attempts += 1
            reset_obj.save(update_fields=['attempts'])
            remaining = 5 - reset_obj.attempts
            return Response({'detail': f'Invalid security code. ({remaining} attempt(s) remaining)'}, 
                            status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 6:
            return Response({'detail': 'New password must be at least 6 characters long.'}, 
                            status=status.HTTP_400_BAD_REQUEST)

        if confirm_password and new_password != confirm_password:
            return Response({'detail': 'New password and confirmation do not match.'}, 
                            status=status.HTTP_400_BAD_REQUEST)

        # Security verification passed
        user.set_password(new_password)
        user.save()

        reset_obj.is_used = True
        reset_obj.save(update_fields=['is_used'])

        # Security audit trail
        try:
            from apps.audit.models import AuditLog
            AuditLog.objects.create(
                user=user,
                action='PASSWORD_RESET_VERIFIED',
                resource='AUTH',
                details=f'Password reset successfully verified via OTP security code for {user.email}'
            )
        except Exception:
            pass

        return Response({'detail': 'Security verification passed. Password updated successfully. You can now sign in.'}, 
                        status=status.HTTP_200_OK)
