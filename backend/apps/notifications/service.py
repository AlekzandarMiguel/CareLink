from .models import Notification
from apps.authentication.models import User
from django.db.models import Q

def broadcast_notification(
    title,
    message,
    notification_type="GENERAL",
    referral=None,
    recipients=None,
    roles=None,
    hospitals=None,
    exclude_users=None,
    fallback_hospital=None
):
    """
    Fan-out notification engine ensuring every relevant user receives
    their own targeted, trackable Notification record with independent read state.
    """
    target_users = set()

    if recipients:
        for r in recipients:
            if r and hasattr(r, 'status') and r.status == User.Status.ACTIVE:
                target_users.add(r)
            elif r and getattr(r, 'is_active', True):
                target_users.add(r)

    if roles:
        role_users = User.objects.filter(role__in=roles, status=User.Status.ACTIVE)
        target_users.update(role_users)

    if hospitals:
        hosp_ids = [h.id if hasattr(h, 'id') else h for h in hospitals if h]
        if hosp_ids:
            hosp_users = User.objects.filter(hospital_id__in=hosp_ids, status=User.Status.ACTIVE)
            target_users.update(hosp_users)

    if exclude_users:
        exclude_ids = {u.id if hasattr(u, 'id') else u for u in exclude_users if u}
        target_users = {u for u in target_users if u.id not in exclude_ids}

    created_count = 0
    if target_users:
        notifications_to_create = []
        for user in target_users:
            notifications_to_create.append(Notification(
                recipient=user,
                hospital=user.hospital,
                title=title,
                message=message,
                referral=referral,
                notification_type=notification_type,
                is_read=False
            ))
        Notification.objects.bulk_create(notifications_to_create)
        created_count = len(notifications_to_create)
    else:
        # Fallback system broadcast
        Notification.objects.create(
            recipient=None,
            hospital=fallback_hospital,
            title=title,
            message=message,
            referral=referral,
            notification_type=notification_type,
            is_read=False
        )
        created_count = 1

    return created_count


def notify_referral_created(referral, creator=None):
    patient_name = referral.patient.name if referral.patient else "Patient"
    service_name = referral.required_service.name if referral.required_service else "Specialized Care"
    hosp_name = referral.requesting_hospital.hospital_name if referral.requesting_hospital else "Facility"

    # 1. Submitting Clinician / Hospital Staff (confirmation)
    if creator:
        broadcast_notification(
            title=f"✅ Referral Submitted: {referral.referral_code}",
            message=f"Successfully submitted {referral.urgency} referral for {patient_name} ({service_name}). Awaiting regional coordinator review.",
            notification_type="REFERRAL_CREATED",
            referral=referral,
            recipients=[creator]
        )

    # 2. Other staff at requesting facility
    broadcast_notification(
        title=f"📋 Outgoing Referral: {referral.referral_code}",
        message=f"{creator.name if creator else 'Clinical staff'} logged a {referral.urgency} referral for {patient_name} ({service_name}).",
        notification_type="REFERRAL_CREATED",
        referral=referral,
        hospitals=[referral.requesting_hospital],
        exclude_users=[creator] if creator else None
    )

    # 3. Regional Triage Coordinators
    is_emergent = (referral.urgency == 'EMERGENCY')
    coord_prefix = "🚨 EMERGENCY TRIAGE" if is_emergent else "📋 New Referral"
    broadcast_notification(
        title=f"{coord_prefix}: {referral.referral_code}",
        message=f"{hosp_name} submitted a {referral.urgency} case for {patient_name} ({service_name}). Matcher review required.",
        notification_type="EMERGENCY_TRIAGE" if is_emergent else "REFERRAL_CREATED",
        referral=referral,
        roles=['COORDINATOR']
    )

    # 4. Platform Administrators
    broadcast_notification(
        title=f"New Referral Logged: {referral.referral_code}",
        message=f"{hosp_name} logged {referral.urgency} referral for {patient_name}.",
        notification_type="REFERRAL_CREATED",
        referral=referral,
        roles=['ADMIN']
    )

    # 5. Direct receiving hospital if pre-selected
    if referral.receiving_hospital:
        broadcast_notification(
            title=f"📥 Incoming Referral: {referral.referral_code}",
            message=f"Direct referral from {hosp_name} for {patient_name} ({service_name}). Clinical review requested.",
            notification_type="INCOMING_REFERRAL",
            referral=referral,
            hospitals=[referral.receiving_hospital]
        )


def notify_status_change(referral, old_status, new_status, user=None):
    patient_name = referral.patient.name if referral.patient else "Patient"
    req_hosp_name = referral.requesting_hospital.hospital_name if referral.requesting_hospital else "Requesting Facility"
    rec_hosp_name = referral.receiving_hospital.hospital_name if referral.receiving_hospital else "Receiving Facility"
    actor_name = user.name if user else "Clinical Coordinator"

    if new_status == 'UNDER_REVIEW':
        # Routed to receiving hospital for intake evaluation
        broadcast_notification(
            title=f"📥 Incoming Referral for Review: {referral.referral_code}",
            message=f"Case for {patient_name} ({referral.urgency}) routed to your hospital by {actor_name}. Clinical intake review requested.",
            notification_type="INCOMING_REFERRAL",
            referral=referral,
            hospitals=[referral.receiving_hospital]
        )
        broadcast_notification(
            title=f"🔄 Referral Routed: {referral.referral_code}",
            message=f"Referral for {patient_name} has been routed to {rec_hosp_name} for intake review.",
            notification_type="STATUS_CHANGE",
            referral=referral,
            hospitals=[referral.requesting_hospital]
        )
        broadcast_notification(
            title=f"Referral Routed: {referral.referral_code}",
            message=f"Case for {patient_name} routed to {rec_hosp_name} by {actor_name}.",
            notification_type="STATUS_CHANGE",
            referral=referral,
            roles=['COORDINATOR'],
            exclude_users=[user] if user else None
        )

    elif new_status == 'ACCEPTED':
        # Receiving hospital accepted the patient
        broadcast_notification(
            title=f"✅ Referral Accepted: {referral.referral_code}",
            message=f"{rec_hosp_name} accepted patient {patient_name}. Patient transport logistics have been automatically initiated.",
            notification_type="REFERRAL_ACCEPTED",
            referral=referral,
            hospitals=[referral.requesting_hospital]
        )
        broadcast_notification(
            title=f"🚑 Transfer Ready for Dispatch: {referral.referral_code}",
            message=f"Patient {patient_name} accepted by {rec_hosp_name}. Vehicle & crew assignment required from {req_hosp_name}.",
            notification_type="TRANSFER_PENDING",
            referral=referral,
            roles=['DISPATCHER']
        )
        broadcast_notification(
            title=f"Referral Accepted: {referral.referral_code}",
            message=f"{rec_hosp_name} accepted {patient_name}. Transfer pending.",
            notification_type="STATUS_CHANGE",
            referral=referral,
            roles=['COORDINATOR']
        )

    elif new_status == 'REJECTED':
        reason = referral.rejection_reason or "Capacity or clinical constraints"
        broadcast_notification(
            title=f"❌ Referral Declined: {referral.referral_code}",
            message=f"{rec_hosp_name} declined {patient_name}. Reason: {reason}. Case returned to coordinator queue for re-matching.",
            notification_type="REFERRAL_REJECTED",
            referral=referral,
            hospitals=[referral.requesting_hospital]
        )
        broadcast_notification(
            title=f"⚠️ Referral Declined: {referral.referral_code}",
            message=f"{rec_hosp_name} declined case for {patient_name} ({reason}). Needs re-routing.",
            notification_type="REFERRAL_REJECTED",
            referral=referral,
            roles=['COORDINATOR']
        )

    elif new_status == 'MORE_INFORMATION_REQUIRED':
        notes = referral.more_info_request_notes or "Additional clinical data requested."
        broadcast_notification(
            title=f"📝 Additional Info Requested: {referral.referral_code}",
            message=f"{rec_hosp_name} requested clinical updates: {notes[:120]}",
            notification_type="MORE_INFO_REQUESTED",
            referral=referral,
            hospitals=[referral.requesting_hospital]
        )
        broadcast_notification(
            title=f"More Info Requested: {referral.referral_code}",
            message=f"{rec_hosp_name} requested clinical details for {patient_name}.",
            notification_type="STATUS_CHANGE",
            referral=referral,
            roles=['COORDINATOR']
        )

    elif new_status == 'CANCELLED':
        broadcast_notification(
            title=f"🚫 Referral Cancelled: {referral.referral_code}",
            message=f"Referral for {patient_name} has been cancelled by {actor_name}.",
            notification_type="STATUS_CHANGE",
            referral=referral,
            hospitals=[referral.requesting_hospital, referral.receiving_hospital],
            roles=['COORDINATOR']
        )

    else:
        # Generic status transition
        broadcast_notification(
            title=f"Referral {referral.referral_code} Status Update",
            message=f"Status changed from {old_status} to {new_status} by {actor_name}.",
            notification_type="STATUS_CHANGE",
            referral=referral,
            hospitals=[referral.requesting_hospital, referral.receiving_hospital],
            roles=['COORDINATOR']
        )


def notify_document_uploaded(referral, document, uploader):
    patient_name = referral.patient.name if referral.patient else "Patient"
    doc_type_name = document.get_document_type_display() if hasattr(document, 'get_document_type_display') else document.document_type
    
    # Notify the counterpart facility
    target_hosp = referral.receiving_hospital if uploader.hospital_id == referral.requesting_hospital_id else referral.requesting_hospital
    if target_hosp:
        broadcast_notification(
            title=f"📎 Document Attached: {referral.referral_code}",
            message=f"{uploader.name} attached {document.filename} ({doc_type_name}) for patient {patient_name}.",
            notification_type="DOCUMENT_UPLOADED",
            referral=referral,
            hospitals=[target_hosp]
        )

    # Notify Coordinators
    broadcast_notification(
        title=f"Document Attached: {referral.referral_code}",
        message=f"{document.filename} uploaded for {patient_name} by {uploader.name}.",
        notification_type="DOCUMENT_UPLOADED",
        referral=referral,
        roles=['COORDINATOR']
    )


def notify_transfer_update(transfer, action_name, actor=None):
    ref = transfer.referral
    patient_name = ref.patient.name if ref and ref.patient else "Patient"
    code = ref.referral_code if ref else f"TR-{transfer.id}"
    vehicle = transfer.vehicle_number or "EMS Unit"
    driver = transfer.driver_name or "EMS Crew"
    dest_name = transfer.destination_hospital.hospital_name if transfer.destination_hospital else "Receiving Facility"
    origin_name = ref.requesting_hospital.hospital_name if ref and ref.requesting_hospital else "Origin Facility"

    if action_name in ['Assigned', 'TRANSFER_ASSIGNED']:
        broadcast_notification(
            title=f"🚑 Transport Assigned: {code}",
            message=f"Ambulance {vehicle} (Driver: {driver}) assigned to transport {patient_name} to {dest_name}.",
            notification_type="TRANSFER_UPDATE",
            referral=ref,
            hospitals=[ref.requesting_hospital, transfer.destination_hospital],
            roles=['COORDINATOR']
        )
    elif action_name in ['DISPATCHED']:
        broadcast_notification(
            title=f"🚑 Unit Dispatched: {code}",
            message=f"Ambulance {vehicle} departed towards {origin_name} for patient pickup.",
            notification_type="TRANSFER_UPDATE",
            referral=ref,
            hospitals=[ref.requesting_hospital, transfer.destination_hospital],
            roles=['COORDINATOR']
        )
    elif action_name in ['PICKED_UP']:
        broadcast_notification(
            title=f"🩺 Patient Picked Up: {code}",
            message=f"Patient {patient_name} secured aboard unit {vehicle} at {origin_name}.",
            notification_type="TRANSFER_UPDATE",
            referral=ref,
            hospitals=[ref.requesting_hospital, transfer.destination_hospital],
            roles=['COORDINATOR']
        )
    elif action_name in ['IN_TRANSIT']:
        broadcast_notification(
            title=f"🚨 En Route: {code}",
            message=f"Unit {vehicle} in transit with patient {patient_name} heading towards {dest_name}.",
            notification_type="TRANSFER_UPDATE",
            referral=ref,
            hospitals=[ref.requesting_hospital, transfer.destination_hospital],
            roles=['COORDINATOR']
        )
    elif action_name in ['ARRIVED']:
        broadcast_notification(
            title=f"🚨 Unit Arrived at Bay: {code}",
            message=f"Ambulance {vehicle} arrived at {dest_name} emergency bay with patient {patient_name}.",
            notification_type="TRANSFER_UPDATE",
            referral=ref,
            hospitals=[ref.requesting_hospital, transfer.destination_hospital],
            roles=['COORDINATOR']
        )
    elif action_name in ['HANDED_OVER']:
        broadcast_notification(
            title=f"🤝 Clinical Handover Complete: {code}",
            message=f"Patient {patient_name} successfully transferred into {dest_name} emergency triage team.",
            notification_type="TRANSFER_UPDATE",
            referral=ref,
            hospitals=[ref.requesting_hospital, transfer.destination_hospital],
            roles=['COORDINATOR']
        )
    elif action_name in ['COMPLETED']:
        broadcast_notification(
            title=f"🏁 Transfer Completed: {code}",
            message=f"Patient transport and admission finalized for {patient_name} at {dest_name}.",
            notification_type="TRANSFER_UPDATE",
            referral=ref,
            hospitals=[ref.requesting_hospital, transfer.destination_hospital],
            roles=['COORDINATOR', 'DISPATCHER']
        )
    else:
        broadcast_notification(
            title=f"Transfer Update: {code}",
            message=f"Transport status updated to {action_name} for patient {patient_name}.",
            notification_type="TRANSFER_UPDATE",
            referral=ref,
            hospitals=[ref.requesting_hospital, transfer.destination_hospital]
        )


def notify_capacity_alert(hospital, available_icu, available_beds, actor=None):
    if available_icu <= 1:
        broadcast_notification(
            title=f"⚠️ Critical Capacity Alert: {hospital.hospital_name}",
            message=f"Critical ICU bed threshold reached ({available_icu} ICU beds available, {available_beds} regular beds). Regional triage matcher advised.",
            notification_type="CAPACITY_ALERT",
            roles=['COORDINATOR', 'ADMIN']
        )


def notify_hospital_registration(hospital):
    broadcast_notification(
        title=f"🏥 New Facility Registration: {hospital.hospital_name}",
        message=f"{hospital.hospital_name} ({hospital.city}, {hospital.province}) has registered for CareLink accreditation. Administrator review required.",
        notification_type="HOSPITAL_REGISTRATION",
        roles=['ADMIN']
    )


def notify_hospital_approval(hospital, action, admin_user, reason=""):
    if action in ['APPROVE', 'ACTIVATE']:
        broadcast_notification(
            title=f"🎉 Facility Accreditation Approved: {hospital.hospital_name}",
            message=f"Your facility has been officially approved by CareLink Administration. You may now initiate and receive regional referrals.",
            notification_type="HOSPITAL_APPROVAL",
            hospitals=[hospital]
        )
        broadcast_notification(
            title=f"Hospital Network Update: {hospital.hospital_name}",
            message=f"{hospital.hospital_name} ({hospital.city}) is now an approved receiving/requesting facility.",
            notification_type="HOSPITAL_APPROVAL",
            roles=['COORDINATOR']
        )
    elif action == 'REJECT':
        broadcast_notification(
            title=f"Facility Registration Declined: {hospital.hospital_name}",
            message=f"Application declined by CareLink Administration. Reason: {reason or 'Incomplete accreditation documentation.'}",
            notification_type="HOSPITAL_APPROVAL",
            hospitals=[hospital]
        )
    elif action == 'SUSPEND':
        broadcast_notification(
            title=f"Facility Suspended: {hospital.hospital_name}",
            message=f"Account temporarily suspended by administration.",
            notification_type="HOSPITAL_APPROVAL",
            hospitals=[hospital],
            roles=['COORDINATOR']
        )
