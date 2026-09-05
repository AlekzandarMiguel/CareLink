import uuid
from django.db import models
from django.conf import settings
from apps.hospitals.models import Hospital, MedicalService, Facility, Specialty

class Patient(models.Model):
    class Sex(models.TextChoices):
        MALE = 'MALE', 'Male'
        FEMALE = 'FEMALE', 'Female'
        OTHER = 'OTHER', 'Other'

    patient_ref_no = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=200)
    age = models.PositiveIntegerField()
    sex = models.CharField(max_length=10, choices=Sex.choices)
    contact_number = models.CharField(max_length=50, blank=True, null=True)
    emergency_status = models.BooleanField(default=False)
    current_condition = models.CharField(max_length=255)
    clinical_summary = models.TextField()
    
    created_by_hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='registered_patients')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} (Ref: {self.patient_ref_no})"

class Referral(models.Model):
    class Urgency(models.TextChoices):
        ROUTINE = 'ROUTINE', 'Routine'
        URGENT = 'URGENT', 'Urgent'
        EMERGENCY = 'EMERGENCY', 'Emergency'

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SUBMITTED = 'SUBMITTED', 'Submitted'
        UNDER_REVIEW = 'UNDER_REVIEW', 'Under Review'
        MORE_INFORMATION_REQUIRED = 'MORE_INFORMATION_REQUIRED', 'More Information Required'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        REJECTED = 'REJECTED', 'Rejected'
        TRANSFER_PENDING = 'TRANSFER_PENDING', 'Transfer Pending'
        TRANSFER_ASSIGNED = 'TRANSFER_ASSIGNED', 'Transfer Assigned'
        DISPATCHED = 'DISPATCHED', 'Dispatched'
        PICKED_UP = 'PICKED_UP', 'Picked Up'
        IN_TRANSIT = 'IN_TRANSIT', 'In Transit'
        ARRIVED = 'ARRIVED', 'Arrived'
        HANDED_OVER = 'HANDED_OVER', 'Handed Over'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    referral_code = models.CharField(max_length=64, unique=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='referrals')
    
    requesting_hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='outgoing_referrals')
    receiving_hospital = models.ForeignKey(Hospital, on_delete=models.SET_NULL, null=True, blank=True, related_name='incoming_referrals')
    
    required_service = models.ForeignKey(MedicalService, on_delete=models.PROTECT, related_name='referrals')
    required_facility = models.ForeignKey(Facility, on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals')
    required_specialty = models.ForeignKey(Specialty, on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals')
    
    urgency = models.CharField(max_length=20, choices=Urgency.choices, default=Urgency.ROUTINE)
    reason_for_referral = models.TextField()
    additional_requirements = models.TextField(blank=True, null=True)
    
    status = models.CharField(max_length=35, choices=Status.choices, default=Status.DRAFT)
    
    rejection_reason = models.TextField(blank=True, null=True)
    more_info_request_notes = models.TextField(blank=True, null=True)
    more_info_response_notes = models.TextField(blank=True, null=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_referrals')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Referral {self.referral_code} ({self.status})"

class ReferralDocument(models.Model):
    class DocType(models.TextChoices):
        REFERRAL_LETTER = 'REFERRAL_LETTER', 'Referral Letter'
        MEDICAL_SUMMARY = 'MEDICAL_SUMMARY', 'Medical Summary'
        LAB_RESULT = 'LAB_RESULT', 'Laboratory Result'
        IMAGING_REPORT = 'IMAGING_REPORT', 'Imaging Report (X-Ray/CT/MRI)'
        OTHER = 'OTHER', 'Other Clinical Document'

    referral = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=30, choices=DocType.choices, default=DocType.REFERRAL_LETTER)
    file = models.FileField(upload_to='referral_docs/%Y/%m/%d/')
    filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document_type} - {self.filename}"

class ReferralStatusHistory(models.Model):
    referral = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name='status_history')
    from_status = models.CharField(max_length=35)
    to_status = models.CharField(max_length=35)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.referral.referral_code}: {self.from_status} -> {self.to_status} at {self.created_at}"

class ReferralMessage(models.Model):
    referral = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referral_messages')
    message = models.TextField()
    is_urgent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Msg by {self.sender.email} on {self.referral.referral_code} ({self.created_at})"
