from django.db import models
from django.conf import settings
from apps.hospitals.models import Hospital

class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    user_email = models.EmailField(blank=True, null=True)
    hospital = models.ForeignKey(Hospital, on_delete=models.SET_NULL, null=True, blank=True)
    hospital_name = models.CharField(max_length=255, blank=True, null=True)
    
    action = models.CharField(max_length=100) # CREATE, UPDATE, APPROVE, REJECT, ACCEPT, STATUS_CHANGE, LOGIN
    resource = models.CharField(max_length=100) # Referral, Hospital, User, Transfer, Document
    resource_id = models.CharField(max_length=100, blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    details = models.TextField(blank=True, null=True)
    previous_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp}] {self.action} on {self.resource} by {self.user_email or 'System'}"
