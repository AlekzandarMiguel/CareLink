from django.db import models

class MedicalService(models.Model):
    name = models.CharField(max_length=150, unique=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Facility(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Specialty(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Hospital(models.Model):
    class OperatingStatus(models.TextChoices):
        OPERATIONAL = 'OPERATIONAL', 'Fully Operational'
        LIMITED = 'LIMITED', 'Limited Capacity'
        EMERGENCY_ONLY = 'EMERGENCY_ONLY', 'Emergency Only'
        MAINTENANCE = 'MAINTENANCE', 'Under Maintenance'
        CLOSED = 'CLOSED', 'Closed'

    class VerificationStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending Verification'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        SUSPENDED = 'SUSPENDED', 'Suspended'

    class HospitalType(models.TextChoices):
        PRIMARY = 'PRIMARY', 'Primary Care Hospital'
        SECONDARY = 'SECONDARY', 'Secondary / General Hospital'
        TERTIARY = 'TERTIARY', 'Tertiary / Level 3 Medical Center'
        SPECIALTY = 'SPECIALTY', 'Specialty Hospital'
        APEX_TRAUMA = 'APEX_TRAUMA', 'Apex Trauma Center'

    hospital_name = models.CharField(max_length=255)
    hospital_code = models.CharField(max_length=50, unique=True)
    hospital_type = models.CharField(max_length=50, choices=HospitalType.choices, default=HospitalType.TERTIARY)
    
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=10, decimal_places=6)
    longitude = models.DecimalField(max_digits=10, decimal_places=6)
    
    contact_number = models.CharField(max_length=50)
    email = models.EmailField(max_length=255)
    emergency_contact = models.CharField(max_length=50, blank=True, null=True)
    
    operating_status = models.CharField(max_length=30, choices=OperatingStatus.choices, default=OperatingStatus.OPERATIONAL)
    verification_status = models.CharField(max_length=30, choices=VerificationStatus.choices, default=VerificationStatus.PENDING)
    
    services = models.ManyToManyField(MedicalService, related_name='hospitals', blank=True)
    facilities = models.ManyToManyField(Facility, related_name='hospitals', blank=True)
    specialties = models.ManyToManyField(Specialty, related_name='hospitals', blank=True)
    
    bed_capacity = models.PositiveIntegerField(default=100)
    available_beds = models.PositiveIntegerField(default=20)
    icu_capacity = models.PositiveIntegerField(default=10)
    available_icu_beds = models.PositiveIntegerField(default=2)
    
    authorized_rep_name = models.CharField(max_length=150, blank=True, null=True)
    authorized_rep_contact = models.CharField(max_length=100, blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    diversion_status = models.BooleanField(default=False)
    on_call_specialists = models.JSONField(default=dict, blank=True)
    temporary_penalties = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.hospital_name} ({self.hospital_code})"
