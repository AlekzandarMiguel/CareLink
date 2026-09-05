from rest_framework import generics, status, views, permissions
from rest_framework.response import Response
from django.db.models import Q
from .models import Hospital, MedicalService, Facility, Specialty
from .serializers import HospitalSerializer, HospitalRegistrationSerializer, MedicalServiceSerializer, FacilitySerializer, SpecialtySerializer
from apps.authentication.permissions import IsAdminUser

class HospitalListCreateView(generics.ListCreateAPIView):
    serializer_class = HospitalSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = Hospital.objects.all().prefetch_related('services', 'facilities', 'specialties')
        user = self.request.user
        
        status_param = self.request.query_params.get('verification_status')
        if status_param:
            if user and user.is_authenticated and user.role == 'ADMIN':
                qs = qs.filter(verification_status=status_param)
            else:
                qs = qs.filter(verification_status='APPROVED')
        elif not (user and user.is_authenticated and user.role == 'ADMIN'):
            qs = qs.filter(verification_status='APPROVED')

        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(hospital_name__icontains=search) |
                Q(city__icontains=search) |
                Q(province__icontains=search) |
                Q(hospital_code__icontains=search)
            )
        
        service_id = self.request.query_params.get('service_id')
        if service_id:
            qs = qs.filter(services__id=service_id)
            
        facility_id = self.request.query_params.get('facility_id')
        if facility_id:
            qs = qs.filter(facilities__id=facility_id)

        return qs.order_by('hospital_name')

    def create(self, request, *args, **kwargs):
        serializer = HospitalRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        hospital = serializer.save()
        from apps.notifications.service import notify_hospital_registration
        notify_hospital_registration(hospital)
        return Response(HospitalSerializer(hospital).data, status=status.HTTP_201_CREATED)

class HospitalDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Hospital.objects.all().prefetch_related('services', 'facilities', 'specialties')
    serializer_class = HospitalSerializer

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            if request.user.role != 'ADMIN' and request.user.hospital_id != obj.id:
                self.permission_denied(request, message="You can only manage your own hospital profile.")

    def perform_update(self, serializer):
        hospital = serializer.save()
        if hospital.available_icu_beds is not None and hospital.available_icu_beds <= 1:
            from apps.notifications.service import notify_capacity_alert
            notify_capacity_alert(hospital, hospital.available_icu_beds, hospital.available_beds, self.request.user)

class HospitalApprovalView(views.APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        action = request.data.get('action')
        try:
            hospital = Hospital.objects.get(pk=pk)
        except Hospital.DoesNotExist:
            return Response({'detail': 'Hospital not found.'}, status=status.HTTP_404_NOT_FOUND)

        reason = request.data.get('reason', '')
        if action == 'APPROVE':
            hospital.verification_status = Hospital.VerificationStatus.APPROVED
            hospital.operating_status = Hospital.OperatingStatus.OPERATIONAL
            hospital.rejection_reason = None
        elif action == 'REJECT':
            hospital.verification_status = Hospital.VerificationStatus.REJECTED
            hospital.rejection_reason = reason or 'Application rejected by administrator.'
        elif action == 'SUSPEND':
            hospital.verification_status = Hospital.VerificationStatus.SUSPENDED
            hospital.operating_status = Hospital.OperatingStatus.CLOSED
        elif action == 'ACTIVATE':
            hospital.verification_status = Hospital.VerificationStatus.APPROVED
            hospital.operating_status = Hospital.OperatingStatus.OPERATIONAL
        else:
            return Response({'detail': 'Invalid action. Supported: APPROVE, REJECT, SUSPEND, ACTIVATE'}, status=status.HTTP_400_BAD_REQUEST)

        hospital.save()
        from apps.notifications.service import notify_hospital_approval
        notify_hospital_approval(hospital, action, request.user, reason=reason)
        return Response(HospitalSerializer(hospital).data)

class MedicalServiceListView(generics.ListCreateAPIView):
    queryset = MedicalService.objects.filter(is_active=True).order_by('name')
    serializer_class = MedicalServiceSerializer
    permission_classes = [permissions.AllowAny]

class FacilityListView(generics.ListCreateAPIView):
    queryset = Facility.objects.filter(is_active=True).order_by('name')
    serializer_class = FacilitySerializer
    permission_classes = [permissions.AllowAny]

class SpecialtyListView(generics.ListCreateAPIView):
    queryset = Specialty.objects.filter(is_active=True).order_by('name')
    serializer_class = SpecialtySerializer
    permission_classes = [permissions.AllowAny]
