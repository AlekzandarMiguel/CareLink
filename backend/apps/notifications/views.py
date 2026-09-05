from rest_framework import generics, views, status, permissions
from rest_framework.response import Response
from django.db.models import Q
from .models import Notification
from .serializers import NotificationSerializer

class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return Notification.objects.none()

        if user.role == 'ADMIN':
            return Notification.objects.all().select_related('referral', 'hospital').order_by('-created_at')[:60]
        
        q = Q(recipient=user)
        if user.hospital_id:
            q |= (Q(hospital_id=user.hospital_id) & Q(recipient__isnull=True))
        
        # Include role broadcasts when recipient is null
        if user.role == 'COORDINATOR':
            q |= (Q(notification_type__in=['REFERRAL_CREATED', 'EMERGENCY_TRIAGE', 'STATUS_CHANGE', 'CAPACITY_ALERT', 'DOCUMENT_UPLOADED', 'TRANSFER_UPDATE']) & Q(recipient__isnull=True))
        elif user.role == 'DISPATCHER':
            q |= (Q(notification_type__in=['TRANSFER_PENDING', 'TRANSFER_UPDATE']) & Q(recipient__isnull=True))
            
        return Notification.objects.filter(q).select_related('referral', 'hospital').order_by('-created_at')[:60]

class MarkNotificationReadView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        try:
            if user.role == 'ADMIN':
                notif = Notification.objects.get(pk=pk)
            else:
                q = Q(pk=pk) & (
                    Q(recipient=user) | 
                    (Q(hospital_id=user.hospital_id) if user.hospital_id else Q()) |
                    Q(recipient__isnull=True)
                )
                notif = Notification.objects.get(q)

            notif.is_read = True
            notif.save(update_fields=['is_read'])
            return Response({'status': 'marked as read'})
        except Notification.DoesNotExist:
            return Response({'detail': 'Notification not found.'}, status=status.HTTP_404_NOT_FOUND)

class MarkAllNotificationsReadView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.role == 'ADMIN':
            Notification.objects.filter(is_read=False).update(is_read=True)
        else:
            q = Q(recipient=user)
            if user.hospital_id:
                q |= (Q(hospital_id=user.hospital_id) & Q(recipient__isnull=True))
            if user.role == 'COORDINATOR':
                q |= (Q(notification_type__in=['REFERRAL_CREATED', 'EMERGENCY_TRIAGE', 'STATUS_CHANGE', 'CAPACITY_ALERT', 'DOCUMENT_UPLOADED', 'TRANSFER_UPDATE']) & Q(recipient__isnull=True))
            elif user.role == 'DISPATCHER':
                q |= (Q(notification_type__in=['TRANSFER_PENDING', 'TRANSFER_UPDATE']) & Q(recipient__isnull=True))
            Notification.objects.filter(q, is_read=False).update(is_read=True)
        return Response({'status': 'all marked as read'})
