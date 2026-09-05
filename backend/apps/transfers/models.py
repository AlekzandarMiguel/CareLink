from django.db import models
from django.conf import settings
from apps.hospitals.models import Hospital
from apps.referrals.models import Referral

class Transfer(models.Model):
    class Status(models.TextChoices):
        TRANSFER_PENDING = 'TRANSFER_PENDING', 'Transfer Pending'
        TRANSFER_ASSIGNED = 'TRANSFER_ASSIGNED', 'Transfer Assigned'
        DISPATCHED = 'DISPATCHED', 'Dispatched'
        PICKED_UP = 'PICKED_UP', 'Picked Up'
        IN_TRANSIT = 'IN_TRANSIT', 'In Transit'
        ARRIVED = 'ARRIVED', 'Arrived'
        HANDED_OVER = 'HANDED_OVER', 'Handed Over'
        COMPLETED = 'COMPLETED', 'Completed'

    referral = models.OneToOneField(Referral, on_delete=models.CASCADE, related_name='transfer')
    dispatcher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='dispatched_transfers')
    
    vehicle_number = models.CharField(max_length=50, blank=True, null=True)
    vehicle_type = models.CharField(max_length=50, default='Advanced Life Support (ALS) Ambulance')
    driver_name = models.CharField(max_length=150, blank=True, null=True)
    driver_contact = models.CharField(max_length=50, blank=True, null=True)
    paramedic_name = models.CharField(max_length=150, blank=True, null=True)
    
    pickup_location = models.CharField(max_length=255)
    destination_hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='incoming_transfers')
    
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.TRANSFER_PENDING)
    
    dispatched_at = models.DateTimeField(null=True, blank=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    in_transit_at = models.DateTimeField(null=True, blank=True)
    arrived_at = models.DateTimeField(null=True, blank=True)
    handed_over_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    handover_notes = models.TextField(blank=True, null=True)
    problem_reports = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Transfer for {self.referral.referral_code} ({self.status})"
