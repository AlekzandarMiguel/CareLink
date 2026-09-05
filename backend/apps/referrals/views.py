from rest_framework import generics, status, views, permissions
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
from .models import Patient, Referral, ReferralDocument, ReferralStatusHistory, ReferralMessage
from .serializers import PatientSerializer, ReferralSerializer, ReferralCreateSerializer, ReferralDocumentSerializer, ReferralMessageSerializer
from .state_machine import ReferralStateMachine
from apps.authentication.permissions import IsSameHospitalOrAdmin
from apps.notifications.service import notify_status_change

class PatientListCreateView(generics.ListCreateAPIView):
    serializer_class = PatientSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role in ['ADMIN', 'COORDINATOR']:
            return Patient.objects.all().order_by('-created_at')
        return Patient.objects.filter(created_by_hospital_id=user.hospital_id).order_by('-created_at')

    def perform_create(self, serializer):
        import uuid
        user = self.request.user
        ref_no = f"PAT-{uuid.uuid4().hex[:8].upper()}"
        serializer.save(patient_ref_no=ref_no, created_by_hospital_id=user.hospital_id)

class ReferralListCreateView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ReferralCreateSerializer
        return ReferralSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Referral.objects.all().select_related(
            'patient', 'requesting_hospital', 'receiving_hospital',
            'required_service', 'required_facility', 'required_specialty', 'created_by'
        ).prefetch_related('documents', 'status_history')

        # Role & Hospital Filtering
        if user.role == 'ADMIN' or user.role == 'COORDINATOR':
            # Global access for platform admin & coordinator
            pass
        elif user.role == 'DISPATCHER':
            # Dispatchers see referrals that are in transfer states
            qs = qs.filter(status__in=[
                'ACCEPTED', 'TRANSFER_PENDING', 'TRANSFER_ASSIGNED',
                'DISPATCHED', 'PICKED_UP', 'IN_TRANSIT', 'ARRIVED', 'HANDED_OVER', 'COMPLETED'
            ])
        elif user.hospital_id:
            # Hospital Staff see outgoing and incoming referrals for their hospital
            tab = self.request.query_params.get('type')
            if tab == 'incoming':
                qs = qs.filter(receiving_hospital_id=user.hospital_id)
            elif tab == 'outgoing':
                qs = qs.filter(requesting_hospital_id=user.hospital_id)
            else:
                qs = qs.filter(Q(requesting_hospital_id=user.hospital_id) | Q(receiving_hospital_id=user.hospital_id))

        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        urgency_param = self.request.query_params.get('urgency')
        if urgency_param:
            qs = qs.filter(urgency=urgency_param)

        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(referral_code__icontains=search) |
                Q(patient__name__icontains=search) |
                Q(patient__patient_ref_no__icontains=search) |
                Q(required_service__name__icontains=search)
            )

        return qs.order_by('-created_at')

class ReferralDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Referral.objects.all().select_related(
        'patient', 'requesting_hospital', 'receiving_hospital',
        'required_service', 'required_facility', 'required_specialty'
    ).prefetch_related('documents', 'status_history')
    serializer_class = ReferralSerializer
    permission_classes = [IsSameHospitalOrAdmin]

class ReferralTransitionView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            referral = Referral.objects.get(pk=pk)
        except Referral.DoesNotExist:
            return Response({'detail': 'Referral not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Check hospital access
        user = request.user
        if user.role != 'ADMIN' and user.role != 'COORDINATOR':
            if user.hospital_id not in [referral.requesting_hospital_id, referral.receiving_hospital_id]:
                return Response({'detail': 'You do not have permission to modify this referral.'}, status=status.HTTP_403_FORBIDDEN)

        target_status = request.data.get('target_status')
        notes = request.data.get('notes', '')
        rejection_reason = request.data.get('rejection_reason')
        more_info = request.data.get('more_info_notes') or request.data.get('more_info') or (notes if target_status == 'MORE_INFORMATION_REQUIRED' else None)
        receiving_hospital_id = request.data.get('receiving_hospital_id')

        # If coordinator routes to receiving hospital
        if receiving_hospital_id:
            referral.receiving_hospital_id = receiving_hospital_id
            if target_status == 'SUBMITTED' or referral.status == 'SUBMITTED':
                target_status = 'UNDER_REVIEW'

        # Validate state transition
        ReferralStateMachine.validate_transition(
            referral=referral,
            new_status=target_status,
            user=user,
            notes=notes,
            rejection_reason=rejection_reason,
            more_info=more_info
        )

        old_status = referral.status
        referral.status = target_status

        if rejection_reason:
            referral.rejection_reason = rejection_reason
        if more_info:
            if target_status == 'MORE_INFORMATION_REQUIRED':
                referral.more_info_request_notes = more_info
            else:
                referral.more_info_response_notes = more_info

        referral.save()

        # If ACCEPTED, automatically create Transfer record in TRANSFER_PENDING
        if target_status == 'ACCEPTED':
            from apps.transfers.models import Transfer
            Transfer.objects.get_or_create(
                referral=referral,
                defaults={
                    'destination_hospital': referral.receiving_hospital,
                    'pickup_location': f"{referral.requesting_hospital.hospital_name}, {referral.requesting_hospital.address}",
                    'status': Transfer.Status.TRANSFER_PENDING
                }
            )

        # Record Status History
        ReferralStatusHistory.objects.create(
            referral=referral,
            from_status=old_status,
            to_status=target_status,
            changed_by=user,
            notes=notes or f"Transitioned from {old_status} to {target_status}"
        )

        # Send notifications
        notify_status_change(referral, old_status, target_status, user)

        return Response(ReferralSerializer(referral).data)

class ReferralDocumentUploadView(views.APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            referral = Referral.objects.get(pk=pk)
        except Referral.DoesNotExist:
            return Response({'detail': 'Referral not found.'}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if user.role != 'ADMIN' and user.hospital_id not in [referral.requesting_hospital_id, referral.receiving_hospital_id]:
            return Response({'detail': 'You do not have permission to upload documents for this referral.'}, status=status.HTTP_403_FORBIDDEN)

        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'detail': 'No file uploaded.'}, status=status.HTTP_400_BAD_REQUEST)

        doc_type = request.data.get('document_type', ReferralDocument.DocType.OTHER)
        filename = file_obj.name

        doc = ReferralDocument.objects.create(
            referral=referral,
            document_type=doc_type,
            file=file_obj,
            filename=filename,
            file_size=file_obj.size,
            uploaded_by=user
        )

        from apps.notifications.service import notify_document_uploaded
        notify_document_uploaded(referral, doc, user)

        return Response(ReferralDocumentSerializer(doc).data, status=status.HTTP_201_CREATED)

class ReferralMessagesView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            referral = Referral.objects.get(pk=pk)
        except Referral.DoesNotExist:
            return Response({'detail': 'Referral not found.'}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if user.role != 'ADMIN' and user.hospital_id not in [referral.requesting_hospital_id, referral.receiving_hospital_id]:
            return Response({'detail': 'You do not have permission to view messages for this referral.'}, status=status.HTTP_403_FORBIDDEN)

        messages = referral.messages.select_related('sender', 'sender__hospital').order_by('created_at')
        return Response(ReferralMessageSerializer(messages, many=True).data)

    def post(self, request, pk):
        try:
            referral = Referral.objects.get(pk=pk)
        except Referral.DoesNotExist:
            return Response({'detail': 'Referral not found.'}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if user.role != 'ADMIN' and user.hospital_id not in [referral.requesting_hospital_id, referral.receiving_hospital_id]:
            return Response({'detail': 'You do not have permission to post messages for this referral.'}, status=status.HTTP_403_FORBIDDEN)

        msg_text = request.data.get('message', '').strip()
        if not msg_text:
            return Response({'detail': 'Message content cannot be empty.'}, status=status.HTTP_400_BAD_REQUEST)

        is_urgent = bool(request.data.get('is_urgent', False))

        message = ReferralMessage.objects.create(
            referral=referral,
            sender=user,
            message=msg_text,
            is_urgent=is_urgent
        )

        from apps.notifications.models import Notification
        from apps.authentication.models import User
        target_hospital_id = referral.receiving_hospital_id if user.hospital_id == referral.requesting_hospital_id else referral.requesting_hospital_id
        if target_hospital_id:
            target_users = User.objects.filter(hospital_id=target_hospital_id, is_active=True)
            alert_prefix = "🚨 [URGENT NOTE]" if is_urgent else "💬 [Case Discussion]"
            hosp_name = user.hospital.hospital_name if user.hospital else 'CareLink Platform'
            for tu in target_users:
                Notification.objects.create(
                    recipient=tu,
                    title=f"{alert_prefix} Referral {referral.referral_code}",
                    message=f"{user.name} ({hosp_name}): {msg_text[:120]}",
                    notification_type='URGENT_CLINICAL_NOTE' if is_urgent else 'CLINICAL_NOTE',
                    referral=referral
                )

        return Response(ReferralMessageSerializer(message).data, status=status.HTTP_201_CREATED)

