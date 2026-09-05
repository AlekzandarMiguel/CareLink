import urllib.request, json, sys, time

BASE_URL = 'http://127.0.0.1:8000/api'

def req(method, endpoint, data=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    body = json.dumps(data).encode('utf-8') if data is not None else None
    r = urllib.request.Request(f"{BASE_URL}{endpoint}", data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8'))

def login(email, pwd):
    s, d = req('POST', '/auth/login/', {'email': email, 'password': pwd})
    if s != 200:
        print(f"Login FAILED for {email}: {d}")
        sys.exit(1)
    return d['access'], d['user']

print("="*80)
print("CARELINK - FULL MULTI-ROLE END-TO-END WORKFLOW SUITE")
print("="*80)

# 1. Login All Roles
print("\n[STEP 1] AUTHENTICATION & ROLE SESSIONS")
admin_tok, u_admin = login('admin@carelink.local', 'AdminPass123!')
staff_a1_tok, u_staff_a1 = login('staff.a1@carelink.local', 'StaffPass123!')
staff_b1_tok, u_staff_b1 = login('staff.b1@carelink.local', 'StaffPass123!')
coord_tok, u_coord = login('coordinator@carelink.local', 'CoordPass123!')
disp_tok, u_disp = login('dispatcher@carelink.local', 'DispatchPass123!')
print("  All 5 user role sessions authenticated successfully.")

# 2. Staff Workflow: Hospital Bed Capacity Update
print("\n[STEP 2] STAFF WORKFLOW: Real-time Bed & ICU Capacity Management")
s, cap = req('PATCH', f"/hospitals/{u_staff_a1['hospital_id']}/", data={
    'available_beds': 35,
    'available_icu_beds': 6
}, token=staff_a1_tok)
assert s == 200, f"Capacity update failed: {cap}"
print(f"  Metro General capacity updated: {cap['available_beds']} beds, {cap['available_icu_beds']} ICU beds open.")

# 3. Staff Workflow: Create Outgoing Referral
print("\n[STEP 3] STAFF WORKFLOW: Patient Intake & Referral Creation")
_, svcs = req('GET', '/hospitals/services/', token=staff_a1_tok)
services = svcs if isinstance(svcs, list) else svcs.get('results', svcs)
cardio = next(s for s in services if 'Cardiology' in s['name'])

s, ref = req('POST', '/referrals/', data={
    'patient_name': 'E2E Validation Patient',
    'patient_age': 52,
    'patient_sex': 'FEMALE',
    'current_condition': 'Acute Coronary Syndrome / NSTEMI',
    'clinical_summary': 'Persistent chest pain with troponin elevation. Local cath lab down for emergency maintenance.',
    'required_service': cardio['id'],
    'urgency': 'EMERGENCY',
    'reason_for_referral': 'Emergency PCI transfer required immediately.'
}, token=staff_a1_tok)
assert s == 201, f"Referral creation failed: {ref}"
ref_id = ref['id']
ref_code = ref['referral_code']

# Retrieve full detail
s, detail = req('GET', f"/referrals/{ref_id}/", token=staff_a1_tok)
assert s == 200, f"Referral detail failed: {detail}"
print(f"  Referral {ref_code} created for {detail['patient_detail']['name']} (Status: {detail['status']})")

# 4. Coordinator Workflow: AI XGBoost Matcher & Routing
print("\n[STEP 4] COORDINATOR WORKFLOW: XGBoost AI Recommendation & Routing")
s, match = req('GET', f"/matching/referrals/{ref_id}/recommendations/", token=coord_tok)
assert s == 200, f"AI Matching failed: {match}"
top = match['recommendations'][0]
print(f"  XGBoost ranked {match['total_candidates']} candidate hospitals.")
print(f"  Top Match: {top['hospital_name']} (Score: {top['match_score']}%, Distance: {top['distance_km']} km)")

s, routed = req('POST', f"/referrals/{ref_id}/transition/", data={
    'target_status': 'UNDER_REVIEW',
    'receiving_hospital_id': u_staff_b1['hospital_id'],
    'notes': f"Routed by coordinator to St. Jude Medical Center."
}, token=coord_tok)
assert s == 200, f"Routing failed: {routed}"
print(f"  Referral {ref_code} routed to {top['hospital_name']}. New status: {routed['status']}")

# 5. Receiving Hospital Staff Workflow: Clinical Review & Acceptance
print("\n[STEP 5] RECEIVING STAFF WORKFLOW: Clinical Review & Acceptance")
s, accepted = req('POST', f"/referrals/{ref_id}/transition/", data={
    'target_status': 'ACCEPTED',
    'notes': 'Cardiology cath team on standby. Patient accepted for immediate PCI.'
}, token=staff_b1_tok)
assert s == 200, f"Acceptance failed: {accepted}"
print(f"  Referral {ref_code} accepted by receiving hospital. Status: {accepted['status']}")

# 6. Dispatcher Workflow: Vehicle & Paramedic Assignment
print("\n[STEP 6] DISPATCHER WORKFLOW: Transfer Generation & Unit Assignment")
s, t_list = req('GET', '/transfers/', token=disp_tok)
transfers = t_list if isinstance(t_list, list) else t_list.get('results', t_list)
t = next(x for x in transfers if x['referral'] == ref_id)
transfer_id = t['id']
print(f"  Transfer record #{transfer_id} automatically generated with status: {t['status']}")

s, assigned = req('POST', f"/transfers/{transfer_id}/assign/", data={
    'vehicle_number': 'AMB-MICU-777',
    'vehicle_type': 'Mobile ICU Unit',
    'driver_name': 'Officer Jack Dempsey',
    'driver_contact': '+1 (555) 777-0101',
    'paramedic_name': 'Paramedic Sarah Connor'
}, token=disp_tok)
assert s == 200, f"Assignment failed: {assigned}"
print(f"  Unit {assigned['vehicle_number']} assigned to Transfer #{transfer_id}. Status: {assigned['status']}")

# 7. Dispatcher Workflow: Complete Milestone Progression
print("\n[STEP 7] DISPATCHER WORKFLOW: Milestone Progression to Destination Handover")
milestones = [
    ('DISPATCHED', 'Ambulance departed base station en route to Metro General.'),
    ('PICKED_UP', 'Patient secured in mobile ICU. Vitals stable.'),
    ('IN_TRANSIT', 'In transit on highway with siren. ETA 12 mins.'),
    ('ARRIVED', 'Arrived at St. Jude emergency bay.'),
    ('HANDED_OVER', 'Clinical handover complete to cath lab team.'),
    ('COMPLETED', 'Transfer finalized and closed in CareLink.')
]
for ms, note in milestones:
    s, m_res = req('POST', f"/transfers/{transfer_id}/status/", data={'status': ms, 'notes': note}, token=disp_tok)
    assert s == 200, f"Milestone {ms} failed: {m_res}"
    print(f"  Transit Milestone -> [{ms}] ({note})")

# 8. Admin Workflow: Analytics, Audit Trail, Hospital & User Oversight
print("\n[STEP 8] ADMIN WORKFLOW: Platform Intelligence & Audit")
s, summary = req('GET', '/analytics/summary/', token=admin_tok)
assert s == 200, f"Analytics summary failed: {summary}"
print(f"  Total Referrals: {summary['total_referrals']} | Acceptance Rate: {summary['acceptance_rate_pct']}%")
print(f"  Active Transfers: {summary['active_transfers']} | Active Users: {summary['total_users']}")

s, charts = req('GET', '/analytics/charts/', token=admin_tok)
assert s == 200, f"Analytics charts failed: {charts}"
print(f"  Analytics Charts generated: {list(charts.keys())}")

s, audit = req('GET', '/audit-logs/', token=admin_tok)
logs = audit if isinstance(audit, list) else audit.get('results', audit)
print(f"  Audit Trail Logged: {len(logs)} activities recorded.")

# 9. In-App Notifications
print("\n[STEP 9] NOTIFICATION SYSTEM: Real-time Alerts & Mark-as-Read")
s, notifs = req('GET', '/notifications/', token=staff_b1_tok)
n_items = notifs if isinstance(notifs, list) else notifs.get('results', notifs)
print(f"  Receiving staff received {len(n_items)} operational notifications.")
s, mark_all = req('POST', '/notifications/read-all/', data={}, token=staff_b1_tok)
assert s == 200, f"Notification mark all failed: {mark_all}"
print("  All notifications marked as read.")

# 10. Public Hospital Registration & Admin Approval Workflow
print("\n[STEP 10] PUBLIC & ADMIN WORKFLOW: Hospital Onboarding & Approval")
now_ts = int(time.time())
s, reg = req('POST', '/hospitals/', data={
    'hospital_name': f'Evergreen Health Center',
    'hospital_code': f'EHC-{now_ts % 10000}',
    'hospital_type': 'SPECIALTY',
    'email': f'admin_{now_ts}@evergreen.org',
    'address': '450 Pine Crest Avenue',
    'city': 'Evergreen City',
    'province': 'North District',
    'latitude': 14.625000,
    'longitude': 120.965000,
    'contact_number': '+1 (555) 321-4567',
    'bed_capacity': 90,
    'available_beds': 18,
    'icu_capacity': 10,
    'available_icu_beds': 3,
    'admin_name': 'Dr. Robert Pine',
    'admin_email': f'pine_{now_ts}@evergreen.org',
    'admin_password': 'EvergreenPass123!'
})
assert s == 201, f"Registration failed: {reg}"
new_hosp_id = reg['id']
print(f"  New hospital registered: {reg['hospital_name']} (Status: {reg['verification_status']})")

s, approved = req('POST', f"/hospitals/{new_hosp_id}/approval/", data={'action': 'APPROVE'}, token=admin_tok)
assert s == 200, f"Approval failed: {approved}"
print(f"  Admin approved {reg['hospital_name']}. Verification Status: {approved['verification_status']}")

print("\n" + "="*80)
print("SUCCESS: ALL USER ROLES & SYSTEM WORKFLOWS VERIFIED END-TO-END!")
print("="*80)
