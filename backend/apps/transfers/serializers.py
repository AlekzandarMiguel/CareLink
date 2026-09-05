from rest_framework import serializers
from .models import Transfer
from apps.referrals.serializers import ReferralSerializer

class TransferSerializer(serializers.ModelSerializer):
    referral_code = serializers.ReadOnlyField(source='referral.referral_code')
    patient_name = serializers.ReadOnlyField(source='referral.patient.name')
    urgency = serializers.ReadOnlyField(source='referral.urgency')
    requesting_hospital_name = serializers.ReadOnlyField(source='referral.requesting_hospital.hospital_name')
    destination_hospital_name = serializers.ReadOnlyField(source='destination_hospital.hospital_name')
    dispatcher_name = serializers.ReadOnlyField(source='dispatcher.name')

    origin_lat = serializers.SerializerMethodField()
    origin_lng = serializers.SerializerMethodField()
    destination_lat = serializers.SerializerMethodField()
    destination_lng = serializers.SerializerMethodField()
    current_lat = serializers.SerializerMethodField()
    current_lng = serializers.SerializerMethodField()
    progress_percent = serializers.SerializerMethodField()

    class Meta:
        model = Transfer
        fields = '__all__'
        read_only_fields = ['id', 'referral', 'created_at', 'updated_at']

    def get_origin_lat(self, obj):
        h = getattr(obj.referral, 'requesting_hospital', None)
        return float(h.latitude) if h and h.latitude else 14.5995

    def get_origin_lng(self, obj):
        h = getattr(obj.referral, 'requesting_hospital', None)
        return float(h.longitude) if h and h.longitude else 120.9842

    def get_destination_lat(self, obj):
        h = obj.destination_hospital
        return float(h.latitude) if h and h.latitude else 14.6091

    def get_destination_lng(self, obj):
        h = obj.destination_hospital
        return float(h.longitude) if h and h.longitude else 121.0223

    def get_progress_percent(self, obj):
        weights = {
            'TRANSFER_PENDING': 5,
            'TRANSFER_ASSIGNED': 15,
            'DISPATCHED': 30,
            'PICKED_UP': 50,
            'IN_TRANSIT': 75,
            'ARRIVED': 90,
            'HANDED_OVER': 95,
            'COMPLETED': 100,
        }
        return weights.get(obj.status, 0)

    def get_current_lat(self, obj):
        o_lat = self.get_origin_lat(obj)
        d_lat = self.get_destination_lat(obj)
        pct = self.get_progress_percent(obj) / 100.0
        return round(o_lat + (d_lat - o_lat) * pct, 6)

    def get_current_lng(self, obj):
        o_lng = self.get_origin_lng(obj)
        d_lng = self.get_destination_lng(obj)
        pct = self.get_progress_percent(obj) / 100.0
        return round(o_lng + (d_lng - o_lng) * pct, 6)

class TransferAssignSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transfer
        fields = ['vehicle_number', 'vehicle_type', 'driver_name', 'driver_contact', 'paramedic_name']
