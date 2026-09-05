from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    referral_code = serializers.ReadOnlyField(source='referral.referral_code')
    target_url = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = '__all__'

    def get_target_url(self, obj):
        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None
        role = user.role if user else None
        ntype = obj.notification_type or ''

        # 1. Referral specific destinations
        if obj.referral_id:
            if ntype == 'TRANSFER_PENDING' and role == 'DISPATCHER':
                return '/dispatcher/pending/'
            if ntype == 'TRANSFER_UPDATE' and role == 'DISPATCHER':
                return '/dispatcher/in-transit/'
            if ntype == 'EMERGENCY_TRIAGE' and role == 'COORDINATOR':
                return f'/referrals/{obj.referral_id}/'
            return f'/referrals/{obj.referral_id}/'

        # 2. Capacity alerts
        if ntype == 'CAPACITY_ALERT':
            if role == 'COORDINATOR':
                return '/coordinator/capacity/'
            elif role == 'STAFF':
                return '/staff/capacity/'
            return '/admin-dashboard/'

        # 3. Hospital registration & approvals
        if ntype == 'HOSPITAL_REGISTRATION':
            if role == 'ADMIN':
                return '/admin/approvals/'
            return '/hospital-search/'

        if ntype == 'HOSPITAL_APPROVAL':
            if role == 'STAFF':
                return '/staff-dashboard/'
            return '/hospital-search/'

        # 4. Fallback by role
        if role == 'ADMIN':
            return '/admin-dashboard/'
        elif role == 'COORDINATOR':
            return '/coordinator-dashboard/'
        elif role == 'DISPATCHER':
            return '/dispatcher-dashboard/'
        return '/staff-dashboard/'
