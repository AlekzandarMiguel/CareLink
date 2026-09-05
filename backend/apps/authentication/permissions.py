from rest_framework import permissions

class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'ADMIN')

class IsHospitalStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'STAFF' and request.user.hospital_id)

class IsCoordinator(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in ['COORDINATOR', 'ADMIN'])

class IsDispatcher(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in ['DISPATCHER', 'ADMIN'])

class IsSameHospitalOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.role in ['ADMIN', 'COORDINATOR']:
            return True
        
        obj_hospital_id = None
        if hasattr(obj, 'hospital_id'):
            obj_hospital_id = obj.hospital_id
        elif hasattr(obj, 'requesting_hospital_id') and hasattr(obj, 'receiving_hospital_id'):
            return request.user.hospital_id in [obj.requesting_hospital_id, obj.receiving_hospital_id]
        elif hasattr(obj, 'referral'):
            ref = obj.referral
            return request.user.hospital_id in [ref.requesting_hospital_id, ref.receiving_hospital_id]
        elif hasattr(obj, 'id') and obj.__class__.__name__ == 'Hospital':
            obj_hospital_id = obj.id

        return obj_hospital_id == request.user.hospital_id
