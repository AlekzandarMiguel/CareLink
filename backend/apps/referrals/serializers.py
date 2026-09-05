import uuid
from rest_framework import serializers
from .models import Patient, Referral, ReferralDocument, ReferralStatusHistory, ReferralMessage
from apps.hospitals.serializers import HospitalSerializer, MedicalServiceSerializer, FacilitySerializer, SpecialtySerializer

class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = '__all__'
        read_only_fields = ['id', 'patient_ref_no', 'created_at']

class ReferralMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.ReadOnlyField(source='sender.name')
    sender_email = serializers.ReadOnlyField(source='sender.email')
    sender_role = serializers.ReadOnlyField(source='sender.role')
    sender_hospital_name = serializers.ReadOnlyField(source='sender.hospital.hospital_name')

    class Meta:
        model = ReferralMessage
        fields = ['id', 'referral', 'sender', 'sender_name', 'sender_email', 'sender_role', 'sender_hospital_name', 'message', 'is_urgent', 'created_at']
        read_only_fields = ['id', 'referral', 'sender', 'created_at']

class ReferralDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.ReadOnlyField(source='uploaded_by.name')

    class Meta:
        model = ReferralDocument
        fields = ['id', 'referral', 'document_type', 'file', 'filename', 'file_size', 'uploaded_by', 'uploaded_by_name', 'uploaded_at']
        read_only_fields = ['id', 'file_size', 'uploaded_by', 'uploaded_at']

class ReferralStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.ReadOnlyField(source='changed_by.name')

    class Meta:
        model = ReferralStatusHistory
        fields = ['id', 'from_status', 'to_status', 'changed_by', 'changed_by_name', 'notes', 'created_at']

class ReferralSerializer(serializers.ModelSerializer):
    patient_detail = PatientSerializer(source='patient', read_only=True)
    requesting_hospital_name = serializers.ReadOnlyField(source='requesting_hospital.hospital_name')
    receiving_hospital_name = serializers.ReadOnlyField(source='receiving_hospital.hospital_name')
    required_service_name = serializers.ReadOnlyField(source='required_service.name')
    required_facility_name = serializers.ReadOnlyField(source='required_facility.name')
    required_specialty_name = serializers.ReadOnlyField(source='required_specialty.name')
    created_by_name = serializers.ReadOnlyField(source='created_by.name')
    documents = ReferralDocumentSerializer(many=True, read_only=True)
    status_history = ReferralStatusHistorySerializer(many=True, read_only=True)
    messages = ReferralMessageSerializer(many=True, read_only=True)

    class Meta:
        model = Referral
        fields = '__all__'
        read_only_fields = ['id', 'referral_code', 'status', 'created_at', 'updated_at']

class ReferralCreateSerializer(serializers.ModelSerializer):
    # Patient fields for nested creation
    patient_name = serializers.CharField(write_only=True)
    patient_age = serializers.IntegerField(write_only=True)
    patient_sex = serializers.ChoiceField(choices=Patient.Sex.choices, write_only=True)
    patient_contact = serializers.CharField(write_only=True, required=False, allow_blank=True)
    current_condition = serializers.CharField(write_only=True)
    clinical_summary = serializers.CharField(write_only=True)

    class Meta:
        model = Referral
        fields = [
            'id', 'referral_code', 'status', 'patient_name', 'patient_age', 'patient_sex', 'patient_contact',
            'current_condition', 'clinical_summary',
            'required_service', 'required_facility', 'required_specialty',
            'receiving_hospital', 'urgency', 'reason_for_referral', 'additional_requirements'
        ]
        read_only_fields = ['id', 'referral_code', 'status']

    def create(self, validated_data):
        user = self.context['request'].user
        p_name = validated_data.pop('patient_name')
        p_age = validated_data.pop('patient_age')
        p_sex = validated_data.pop('patient_sex')
        p_contact = validated_data.pop('patient_contact', '')
        curr_cond = validated_data.pop('current_condition')
        clin_sum = validated_data.pop('clinical_summary')

        ref_no = f"PAT-{uuid.uuid4().hex[:8].upper()}"
        patient = Patient.objects.create(
            patient_ref_no=ref_no,
            name=p_name,
            age=p_age,
            sex=p_sex,
            contact_number=p_contact,
            emergency_status=(validated_data.get('urgency') == Referral.Urgency.EMERGENCY),
            current_condition=curr_cond,
            clinical_summary=clin_sum,
            created_by_hospital_id=user.hospital_id or validated_data.get('requesting_hospital_id')
        )

        referral_code = f"REF-{uuid.uuid4().hex[:8].upper()}"
        initial_status = Referral.Status.SUBMITTED if validated_data.get('receiving_hospital') else Referral.Status.SUBMITTED

        referral = Referral.objects.create(
            referral_code=referral_code,
            patient=patient,
            requesting_hospital_id=user.hospital_id,
            status=initial_status,
            created_by=user,
            **validated_data
        )

        ReferralStatusHistory.objects.create(
            referral=referral,
            from_status='NONE',
            to_status=referral.status,
            changed_by=user,
            notes='Referral created and submitted.'
        )

        from apps.notifications.service import notify_referral_created
        notify_referral_created(referral, creator=user)

        return referral
