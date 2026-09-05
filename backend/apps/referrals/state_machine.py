from rest_framework.exceptions import ValidationError

class ReferralStateMachine:
    VALID_TRANSITIONS = {
        'DRAFT': ['SUBMITTED', 'CANCELLED'],
        'SUBMITTED': ['UNDER_REVIEW', 'ACCEPTED', 'REJECTED', 'MORE_INFORMATION_REQUIRED', 'CANCELLED'],
        'UNDER_REVIEW': ['ACCEPTED', 'REJECTED', 'MORE_INFORMATION_REQUIRED', 'CANCELLED'],
        'MORE_INFORMATION_REQUIRED': ['UNDER_REVIEW', 'SUBMITTED', 'ACCEPTED', 'REJECTED', 'CANCELLED'],
        'ACCEPTED': ['TRANSFER_PENDING', 'TRANSFER_ASSIGNED', 'CANCELLED'],
        'TRANSFER_PENDING': ['TRANSFER_ASSIGNED', 'CANCELLED'],
        'TRANSFER_ASSIGNED': ['DISPATCHED', 'CANCELLED'],
        'DISPATCHED': ['PICKED_UP', 'CANCELLED'],
        'PICKED_UP': ['IN_TRANSIT', 'CANCELLED'],
        'IN_TRANSIT': ['ARRIVED', 'CANCELLED'],
        'ARRIVED': ['HANDED_OVER', 'COMPLETED'],
        'HANDED_OVER': ['COMPLETED'],
        'REJECTED': [],
        'COMPLETED': [],
        'CANCELLED': [],
    }

    @classmethod
    def can_transition(cls, current_status, new_status):
        allowed = cls.VALID_TRANSITIONS.get(current_status, [])
        return new_status in allowed

    @classmethod
    def validate_transition(cls, referral, new_status, user, notes=None, rejection_reason=None, more_info=None):
        if not cls.can_transition(referral.status, new_status):
            raise ValidationError({
                'detail': f'Invalid status transition from {referral.status} to {new_status}.'
            })

        # Role checks
        if new_status in ['ACCEPTED', 'REJECTED', 'MORE_INFORMATION_REQUIRED']:
            if user.role != 'ADMIN' and user.hospital_id != referral.receiving_hospital_id:
                raise ValidationError({
                    'detail': 'Only authorized personnel from the receiving hospital or Admin can perform this action.'
                })
            if new_status == 'REJECTED' and not rejection_reason:
                raise ValidationError({
                    'detail': 'A rejection reason is strictly required when rejecting a referral.'
                })
            if new_status == 'MORE_INFORMATION_REQUIRED' and not more_info:
                raise ValidationError({
                    'detail': 'Specific notes describing the required information must be provided.'
                })

        if new_status in ['DISPATCHED', 'PICKED_UP', 'IN_TRANSIT', 'ARRIVED', 'HANDED_OVER', 'COMPLETED']:
            if user.role not in ['DISPATCHER', 'COORDINATOR', 'ADMIN']:
                raise ValidationError({
                    'detail': 'Only Dispatchers, Coordinators, or Admins can update transport and completion states.'
                })
