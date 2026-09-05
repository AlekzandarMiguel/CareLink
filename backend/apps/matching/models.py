from django.db import models
from django.conf import settings
from apps.referrals.models import Referral
from apps.hospitals.models import Hospital

class CoordinatorOverride(models.Model):
    class ReasonCode(models.TextChoices):
        CT_SCAN_OFFLINE = 'CT_SCAN_OFFLINE', 'CT Scanner / Imaging Down'
        SURGEON_UNAVAILABLE = 'SURGEON_UNAVAILABLE', 'On-Call Specialist / Surgeon Engaged'
        EMERGENCY_BAY_SATURATED = 'EMERGENCY_BAY_SATURATED', 'Emergency Bay at Physical Capacity'
        EQUIPMENT_MAINTENANCE = 'EQUIPMENT_MAINTENANCE', 'Critical Equipment in Maintenance'
        PATIENT_FAMILY_REQUEST = 'PATIENT_FAMILY_REQUEST', 'Patient or Family Facility Preference'
        PHYSICIAN_DISCRETION = 'PHYSICIAN_DISCRETION', 'Referring Physician Clinical Discretion'
        TRANSPORT_CONSTRAINTS = 'TRANSPORT_CONSTRAINTS', 'Ambulance Travel Time or Corridor Constraint'
        OTHER = 'OTHER', 'Other Clinical / Operational Justification'

    referral = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name='coordinator_overrides')
    recommended_hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='recommended_overrides')
    selected_hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='selected_overrides')
    reason_code = models.CharField(max_length=50, choices=ReasonCode.choices, default=ReasonCode.PHYSICIAN_DISCRETION)
    justification_notes = models.TextField(blank=True, null=True)
    coordinator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='submitted_overrides')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Override for {self.referral.referral_code}: {self.recommended_hospital.hospital_name} -> {self.selected_hospital.hospital_name} ({self.reason_code})"
