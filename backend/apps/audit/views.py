from rest_framework import generics, permissions
from .models import AuditLog
from .serializers import AuditLogSerializer
from apps.authentication.permissions import IsAdminUser

class AuditLogListView(generics.ListAPIView):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        qs = AuditLog.objects.all()
        action = self.request.query_params.get('action')
        resource = self.request.query_params.get('resource')
        if action:
            qs = qs.filter(action__icontains=action)
        if resource:
            qs = qs.filter(resource__icontains=resource)
        return qs[:100]
