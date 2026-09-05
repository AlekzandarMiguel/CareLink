from rest_framework import serializers
from .models import Hospital, MedicalService, Facility, Specialty

class MedicalServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalService
        fields = '__all__'

class FacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = '__all__'

class SpecialtySerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialty
        fields = '__all__'

class HospitalSerializer(serializers.ModelSerializer):
    services_detail = MedicalServiceSerializer(source='services', many=True, read_only=True)
    facilities_detail = FacilitySerializer(source='facilities', many=True, read_only=True)
    specialties_detail = SpecialtySerializer(source='specialties', many=True, read_only=True)
    staff_count = serializers.SerializerMethodField()

    class Meta:
        model = Hospital
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_staff_count(self, obj):
        return obj.staff_members.count()

class HospitalRegistrationSerializer(serializers.ModelSerializer):
    admin_name = serializers.CharField(write_only=True)
    admin_email = serializers.EmailField(write_only=True)
    admin_password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = Hospital
        fields = [
            'hospital_name', 'hospital_code', 'hospital_type', 'address', 'city', 'province',
            'latitude', 'longitude', 'contact_number', 'email', 'emergency_contact',
            'bed_capacity', 'available_beds', 'icu_capacity', 'available_icu_beds',
            'services', 'facilities', 'specialties',
            'authorized_rep_name', 'authorized_rep_contact',
            'admin_name', 'admin_email', 'admin_password'
        ]

    def create(self, validated_data):
        admin_name = validated_data.pop('admin_name')
        admin_email = validated_data.pop('admin_email')
        admin_password = validated_data.pop('admin_password')
        services = validated_data.pop('services', [])
        facilities = validated_data.pop('facilities', [])
        specialties = validated_data.pop('specialties', [])

        validated_data['verification_status'] = Hospital.VerificationStatus.PENDING
        hospital = Hospital.objects.create(**validated_data)
        
        if services:
            hospital.services.set(services)
        if facilities:
            hospital.facilities.set(facilities)
        if specialties:
            hospital.specialties.set(specialties)

        from django.contrib.auth import get_user_model
        User = get_user_model()
        User.objects.create_user(
            email=admin_email,
            name=admin_name,
            password=admin_password,
            hospital=hospital,
            role=User.Role.STAFF,
            status=User.Status.ACTIVE,
            position='Hospital Administrator'
        )

        return hospital
