from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.hospitals.models import Hospital, MedicalService, Facility
from apps.referrals.models import Patient, Referral, ReferralStatusHistory
from apps.transfers.models import Transfer
from apps.audit.models import AuditLog
from apps.matching.matcher import haversine_distance, XGBHospitalMatcher

User = get_user_model()

class CareLinkCompleteTestSuite(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        self.service = MedicalService.objects.create(name='Cardiology & Cardiac Surgery', category='Cardiovascular')
        self.facility = Facility.objects.create(name='Cardiac Catheterization Lab')
        
        self.hosp_a = Hospital.objects.create(
            hospital_name='Hospital A',
            hospital_code='HOSP-A',
            hospital_type='SECONDARY',
            address='100 Main St',
            city='Metropolis',
            province='Central',
            latitude=14.600000,
            longitude=120.980000,
            bed_capacity=100,
            available_beds=15,
            icu_capacity=10,
            available_icu_beds=2,
            verification_status='APPROVED',
            operating_status='OPERATIONAL'
        )
        
        self.hosp_b = Hospital.objects.create(
            hospital_name='Hospital B',
            hospital_code='HOSP-B',
            hospital_type='TERTIARY',
            address='200 Health Ave',
            city='Metropolis',
            province='Central',
            latitude=14.650000,
            longitude=121.020000,
            bed_capacity=200,
            available_beds=30,
            icu_capacity=20,
            available_icu_beds=5,
            verification_status='APPROVED',
            operating_status='OPERATIONAL'
        )
        self.hosp_b.services.add(self.service)
        self.hosp_b.facilities.add(self.facility)

        self.admin_user = User.objects.create_superuser(
            email='admin@test.local',
            name='Test Admin',
            password='Password123!'
        )
        
        self.staff_a1 = User.objects.create_user(
            email='staff.a1@test.local',
            name='Staff A1',
            password='Password123!',
            role=User.Role.STAFF,
            hospital=self.hosp_a
        )
        
        self.staff_a2 = User.objects.create_user(
            email='staff.a2@test.local',
            name='Staff A2',
            password='Password123!',
            role=User.Role.STAFF,
            hospital=self.hosp_a
        )
        
        self.staff_b1 = User.objects.create_user(
            email='staff.b1@test.local',
            name='Staff B1',
            password='Password123!',
            role=User.Role.STAFF,
            hospital=self.hosp_b
        )
        
        self.coordinator = User.objects.create_user(
            email='coord@test.local',
            name='Test Coordinator',
            password='Password123!',
            role=User.Role.COORDINATOR
        )

        self.dispatcher = User.objects.create_user(
            email='dispatcher@test.local',
            name='Test Dispatcher',
            password='Password123!',
            role=User.Role.DISPATCHER
        )

    def test_01_authentication_and_jwt(self):
        res = self.client.post('/api/auth/login/', {
            'email': 'staff.a1@test.local',
            'password': 'Password123!'
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn('access', res.data)
        self.assertEqual(res.data['user']['hospital_id'], self.hosp_a.id)

    def test_02_haversine_distance_and_matching(self):
        dist = haversine_distance(14.600000, 120.980000, 14.650000, 121.020000)
        self.assertGreater(dist, 0.0)
        self.assertLess(dist, 20.0)

        patient = Patient.objects.create(
            patient_ref_no='PAT-TEST01',
            name='Jane Patient',
            age=45,
            sex='FEMALE',
            current_condition='Chest Pain',
            clinical_summary='ECG abnormal',
            created_by_hospital=self.hosp_a
        )
        referral = Referral.objects.create(
            referral_code='REF-TEST01',
            patient=patient,
            requesting_hospital=self.hosp_a,
            required_service=self.service,
            required_facility=self.facility,
            urgency='EMERGENCY',
            reason_for_referral='Requires Cath Lab'
        )

        ranks = XGBHospitalMatcher.rank_hospitals_for_referral(referral)
        self.assertTrue(len(ranks) >= 1)
        self.assertEqual(ranks[0]['hospital_id'], self.hosp_b.id)
        self.assertTrue(ranks[0]['is_eligible'])
        self.assertGreaterEqual(ranks[0]['match_score'], 50)

    def test_03_referral_lifecycle_and_multi_staff_access(self):
        self.client.force_authenticate(user=self.staff_a1)
        res = self.client.post('/api/referrals/', {
            'patient_name': 'John Doe',
            'patient_age': 50,
            'patient_sex': 'MALE',
            'current_condition': 'Acute Coronary Syndrome',
            'clinical_summary': 'Severe chest tightness',
            'required_service': self.service.id,
            'receiving_hospital': self.hosp_b.id,
            'urgency': 'URGENT',
            'reason_for_referral': 'Specialized cardiology required'
        })
        self.assertEqual(res.status_code, 201)
        ref_id = res.data['id']

        # Multi-Staff access within same hospital
        self.client.force_authenticate(user=self.staff_a2)
        res_view = self.client.get(f'/api/referrals/{ref_id}/')
        self.assertEqual(res_view.status_code, 200)

        # Receiving hospital accepts
        self.client.force_authenticate(user=self.staff_b1)
        res_accept = self.client.post(f'/api/referrals/{ref_id}/transition/', {
            'target_status': 'ACCEPTED',
            'notes': 'Bed and cath lab prepared.'
        })
        self.assertEqual(res_accept.status_code, 200)
        self.assertEqual(res_accept.data['status'], 'ACCEPTED')

        # Transfer record verification
        transfer = Transfer.objects.get(referral_id=ref_id)
        self.assertEqual(transfer.status, Transfer.Status.TRANSFER_PENDING)

        # Dispatcher workflow
        self.client.force_authenticate(user=self.dispatcher)
        res_assign = self.client.post(f'/api/transfers/{transfer.id}/assign/', {
            'vehicle_number': 'AMB-TEST-01',
            'driver_name': 'Officer Bob'
        })
        self.assertEqual(res_assign.status_code, 200)
        self.assertEqual(res_assign.data['status'], 'TRANSFER_ASSIGNED')

        self.client.post(f'/api/transfers/{transfer.id}/status/', {'status': 'DISPATCHED'})
        self.client.post(f'/api/transfers/{transfer.id}/status/', {'status': 'PICKED_UP'})
        self.client.post(f'/api/transfers/{transfer.id}/status/', {'status': 'IN_TRANSIT'})
        self.client.post(f'/api/transfers/{transfer.id}/status/', {'status': 'ARRIVED'})
        res_final = self.client.post(f'/api/transfers/{transfer.id}/status/', {
            'status': 'HANDED_OVER',
            'notes': 'Patient handed over to emergency triage team.'
        })
        self.assertEqual(res_final.status_code, 200)
        self.assertEqual(res_final.data['status'], 'HANDED_OVER')

    def test_04_hospital_isolation_and_security(self):
        # Staff A1 cannot update Hospital B's details
        self.client.force_authenticate(user=self.staff_a1)
        res = self.client.patch(f'/api/hospitals/{self.hosp_b.id}/', {'hospital_name': 'Hacked Name'})
        self.assertEqual(res.status_code, 403)

        # Admin can approve/modify hospitals
        self.client.force_authenticate(user=self.admin_user)
        res_admin = self.client.post(f'/api/hospitals/{self.hosp_b.id}/approval/', {'action': 'SUSPEND'})
        self.assertEqual(res_admin.status_code, 200)
        self.hosp_b.refresh_from_db()
        self.assertEqual(self.hosp_b.verification_status, 'SUSPENDED')
