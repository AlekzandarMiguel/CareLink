from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import LoginLog

User = get_user_model()

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        
        if user.status != User.Status.ACTIVE:
            raise serializers.ValidationError({"detail": "This account is inactive or suspended. Please contact administrator."})
        
        if user.hospital and user.hospital.verification_status != 'APPROVED' and user.role != User.Role.ADMIN:
            raise serializers.ValidationError({"detail": "Your associated hospital is not yet approved or has been suspended."})
        
        request = self.context.get('request')
        ip = None
        ua = None
        if request:
            ip = request.META.get('REMOTE_ADDR')
            ua = request.META.get('HTTP_USER_AGENT', '')
        LoginLog.objects.create(user=user, ip_address=ip, user_agent=ua, success=True)
        
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        data['user'] = {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'role': user.role,
            'status': user.status,
            'hospital_id': user.hospital_id,
            'hospital_name': user.hospital.hospital_name if user.hospital else None,
            'position': user.position,
        }
        return data

class UserSerializer(serializers.ModelSerializer):
    hospital_name = serializers.ReadOnlyField(source='hospital.hospital_name')

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'role', 'status', 'hospital', 'hospital_name', 'contact_number', 'position', 'last_login', 'created_at']
        read_only_fields = ['id', 'last_login', 'created_at']

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'password', 'role', 'status', 'hospital', 'contact_number', 'position']

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user
