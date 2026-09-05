from rest_framework import generics, status, views, permissions
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q
from .models import Transfer
from .serializers import TransferSerializer, TransferAssignSerializer
from apps.referrals.models import Referral, ReferralStatusHistory
from apps.notifications.service import notify_transfer_update

class TransferListView(generics.ListAPIView):
    serializer_class = TransferSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Transfer.objects.all().select_related('referral', 'referral__patient', 'destination_hospital', 'dispatcher')
        
        if user.role in ['ADMIN', 'COORDINATOR', 'DISPATCHER']:
            pass
        elif user.hospital_id:
            qs = qs.filter(
                Q(referral__requesting_hospital_id=user.hospital_id) |
                Q(destination_hospital_id=user.hospital_id)
            )

        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        return qs.order_by('-created_at')

class TransferDetailView(generics.RetrieveAPIView):
    queryset = Transfer.objects.all().select_related('referral', 'referral__patient', 'destination_hospital', 'dispatcher')
    serializer_class = TransferSerializer

class TransferAssignView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            transfer = Transfer.objects.get(pk=pk)
        except Transfer.DoesNotExist:
            return Response({'detail': 'Transfer not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = TransferAssignSerializer(transfer, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            dispatcher=request.user,
            status=Transfer.Status.TRANSFER_ASSIGNED
        )

        transfer.referral.status = Referral.Status.TRANSFER_ASSIGNED
        transfer.referral.save(update_fields=['status'])

        ReferralStatusHistory.objects.create(
            referral=transfer.referral,
            from_status=Referral.Status.TRANSFER_PENDING,
            to_status=Referral.Status.TRANSFER_ASSIGNED,
            changed_by=request.user,
            notes=f"Vehicle {transfer.vehicle_number} assigned. Driver: {transfer.driver_name}"
        )

        notify_transfer_update(transfer, 'Assigned')
        return Response(TransferSerializer(transfer).data)

class TransferStatusUpdateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            transfer = Transfer.objects.get(pk=pk)
        except Transfer.DoesNotExist:
            return Response({'detail': 'Transfer not found.'}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get('status')
        notes = request.data.get('notes', '')
        now = timezone.now()

        old_status = transfer.status
        transfer.status = new_status

        if new_status == Transfer.Status.DISPATCHED:
            transfer.dispatched_at = now
            transfer.referral.status = Referral.Status.DISPATCHED
        elif new_status == Transfer.Status.PICKED_UP:
            transfer.picked_up_at = now
            transfer.referral.status = Referral.Status.PICKED_UP
        elif new_status == Transfer.Status.IN_TRANSIT:
            transfer.in_transit_at = now
            transfer.referral.status = Referral.Status.IN_TRANSIT
        elif new_status == Transfer.Status.ARRIVED:
            transfer.arrived_at = now
            transfer.referral.status = Referral.Status.ARRIVED
        elif new_status == Transfer.Status.HANDED_OVER:
            transfer.handed_over_at = now
            transfer.handover_notes = notes
            transfer.referral.status = Referral.Status.HANDED_OVER
        elif new_status == Transfer.Status.COMPLETED:
            transfer.completed_at = now
            transfer.referral.status = Referral.Status.COMPLETED

        transfer.save()
        transfer.referral.save(update_fields=['status'])

        ReferralStatusHistory.objects.create(
            referral=transfer.referral,
            from_status=old_status,
            to_status=new_status,
            changed_by=request.user,
            notes=notes or f"Transit progress updated to {new_status}"
        )

        notify_transfer_update(transfer, new_status)
        return Response(TransferSerializer(transfer).data)
