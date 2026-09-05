import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.join(os.getcwd(), 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carelink_core.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.hospitals.models import Hospital, MedicalService, Facility, Specialty
from apps.referrals.models import Patient, Referral, ReferralStatusHistory, ReferralDocument
from apps.transfers.models import Transfer
from apps.audit.models import AuditLog
from apps.notifications.models import Notification

User = get_user_model()

def seed_database():
    print("="*60)
    print("Populating CareLink Database with Realistic Development Seed Data")
    print("="*60)

    # 1. Create Medical Services
    services_data = [
        ("Emergency & Trauma Care", "Emergency", "24/7 Acute trauma, resuscitation, and critical emergency care."),
        ("Cardiology & Cardiac Surgery", "Cardiovascular", "Interventional cardiology, cath lab, and cardiac ICU."),
        ("Neurology & Neurosurgery", "Neurosciences", "Stroke unit, brain trauma, and neurosurgical procedures."),
        ("General & Laparoscopic Surgery", "Surgical", "Emergency exploratory laparotomy and complex abdominal surgery."),
        ("Pediatrics & Neonatal Care", "Pediatrics", "Specialized pediatric ward and neonatal intensive care (NICU)."),
        ("Obstetrics & High-Risk Pregnancy", "Maternal", "Labor suites, high-risk maternal delivery, and emergency C-section."),
        ("Orthopedics & Spine Surgery", "Surgical", "Complex fracture reduction, joint reconstruction, and spinal fixation."),
        ("Nephrology & Hemodialysis", "Internal Medicine", "Acute renal support, CRRT, and continuous dialysis units."),
        ("Oncology & Chemotherapy", "Oncology", "Medical oncology, infusion center, and surgical tumor resection."),
        ("Intensive Care Medicine (ICU)", "Critical Care", "Advanced mechanical ventilation and hemodynamic monitoring.")
    ]

    service_objs = {}
    for name, cat, desc in services_data:
        obj, _ = MedicalService.objects.get_or_create(
            name=name,
            defaults={'category': cat, 'description': desc, 'is_active': True}
        )
        service_objs[name] = obj
    print(f"Created {len(service_objs)} Medical Services.")

    # 2. Create Facilities
    facilities_data = [
        ("Emergency Department (Level 3)", "Comprehensive emergency care facility with triage and resuscitation bay."),
        ("Intensive Care Unit (ICU)", "Dedicated adult ICU beds with dedicated critical care ventilators."),
        ("Pediatric ICU (PICU)", "Specialized pediatric critical care beds and pediatric monitoring."),
        ("Neonatal ICU (NICU)", "Specialized incubators and neonatal life support."),
        ("Cardiac Catheterization Lab", "Digital fluoroscopy for coronary angiography and stenting."),
        ("Operating Theatres Suite (4 ORs)", "Laminar flow sterile surgical suites for emergency operations."),
        ("CT & MRI Imaging Center", "64-slice CT Scanner and 1.5T MRI for fast diagnostic triage."),
        ("Blood Bank & Diagnostic Pathology", "24/7 cross-matching and emergency uncrossmatched O-neg blood supply.")
    ]

    facility_objs = {}
    for name, desc in facilities_data:
        obj, _ = Facility.objects.get_or_create(
            name=name,
            defaults={'description': desc, 'is_active': True}
        )
        facility_objs[name] = obj
    print(f"Created {len(facility_objs)} Facilities.")

    # 3. Create Specialties
    specialties_data = [
        ("Emergency Medicine", "Acute medical care specialists"),
        ("Cardiovascular Surgery", "Heart and vascular surgical specialists"),
        ("Neurosurgery", "Brain and spinal surgery specialists"),
        ("Trauma & Orthopedic Surgery", "Bone and complex trauma specialists"),
        ("Pediatric Critical Care", "Children life support specialists"),
        ("Maternal-Fetal Medicine", "High-risk pregnancy specialists")
    ]
    specialty_objs = {}
    for name, desc in specialties_data:
        obj, _ = Specialty.objects.get_or_create(name=name, defaults={'description': desc})
        specialty_objs[name] = obj
    print(f"Created {len(specialty_objs)} Specialties.")

    # 4. Create Authentic Philippine Hospitals (Metro Manila Network)
    hospitals_data = [
        {
            'name': 'Philippine General Hospital (PGH)',
            'code': 'PGH-MNL-01',
            'type': Hospital.HospitalType.APEX_TRAUMA,
            'address': 'Taft Avenue, Ermita',
            'city': 'Manila',
            'province': 'Metro Manila',
            'lat': 14.579400,
            'lng': 120.985300,
            'contact': '+63 (2) 8554-8400',
            'email': 'referrals@pgh.gov.ph',
            'emergency': '+63 (2) 8554-8400 loc 2001',
            'beds': 1500, 'avail_beds': 95,
            'icu': 60, 'avail_icu': 8,
            'services': ["Emergency & Trauma Care", "General & Laparoscopic Surgery", "Neurology & Neurosurgery", "Orthopedics & Spine Surgery", "Intensive Care Medicine (ICU)", "Obstetrics & High-Risk Pregnancy", "Nephrology & Hemodialysis", "Pediatrics & Neonatal Care"],
            'facilities': ["Emergency Department (Level 3)", "Intensive Care Unit (ICU)", "Operating Theatres Suite (4 ORs)", "CT & MRI Imaging Center", "Blood Bank & Diagnostic Pathology"],
        },
        {
            'name': 'Philippine Heart Center (PHC)',
            'code': 'PHC-QC-02',
            'type': Hospital.HospitalType.SPECIALTY,
            'address': 'East Avenue, Diliman',
            'city': 'Quezon City',
            'province': 'Metro Manila',
            'lat': 14.641600,
            'lng': 121.049400,
            'contact': '+63 (2) 8925-2401',
            'email': 'cardiac.triage@phc.gov.ph',
            'emergency': '+63 (2) 8925-2401 loc 1111',
            'beds': 400, 'avail_beds': 45,
            'icu': 45, 'avail_icu': 9,
            'services': ["Cardiology & Cardiac Surgery", "Intensive Care Medicine (ICU)", "Emergency & Trauma Care", "General & Laparoscopic Surgery"],
            'facilities': ["Cardiac Catheterization Lab", "Intensive Care Unit (ICU)", "Operating Theatres Suite (4 ORs)", "CT & MRI Imaging Center", "Blood Bank & Diagnostic Pathology"],
        },
        {
            'name': 'National Kidney and Transplant Institute (NKTI)',
            'code': 'NKTI-QC-03',
            'type': Hospital.HospitalType.SPECIALTY,
            'address': 'East Avenue, Central District',
            'city': 'Quezon City',
            'province': 'Metro Manila',
            'lat': 14.642800,
            'lng': 121.046800,
            'contact': '+63 (2) 8981-0300',
            'email': 'renal.referrals@nkti.gov.ph',
            'emergency': '+63 (2) 8981-0300 loc 1005',
            'beds': 380, 'avail_beds': 38,
            'icu': 30, 'avail_icu': 6,
            'services': ["Nephrology & Hemodialysis", "General & Laparoscopic Surgery", "Intensive Care Medicine (ICU)", "Emergency & Trauma Care"],
            'facilities': ["Intensive Care Unit (ICU)", "Operating Theatres Suite (4 ORs)", "CT & MRI Imaging Center", "Blood Bank & Diagnostic Pathology"],
        },
        {
            'name': "Philippine Children's Medical Center (PCMC)",
            'code': 'PCMC-QC-04',
            'type': Hospital.HospitalType.SPECIALTY,
            'address': 'Quezon Avenue cor. Agham Road',
            'city': 'Quezon City',
            'province': 'Metro Manila',
            'lat': 14.645000,
            'lng': 121.041000,
            'contact': '+63 (2) 8588-9900',
            'email': 'pediatric.intake@pcmc.gov.ph',
            'emergency': '+63 (2) 8588-9900 loc 202',
            'beds': 250, 'avail_beds': 32,
            'icu': 35, 'avail_icu': 7,
            'services': ["Pediatrics & Neonatal Care", "Intensive Care Medicine (ICU)", "General & Laparoscopic Surgery"],
            'facilities': ["Pediatric ICU (PICU)", "Neonatal ICU (NICU)", "Emergency Department (Level 3)", "Operating Theatres Suite (4 ORs)"],
        },
        {
            'name': 'East Avenue Medical Center (EAMC)',
            'code': 'EAMC-QC-05',
            'type': Hospital.HospitalType.APEX_TRAUMA,
            'address': 'East Avenue, Diliman',
            'city': 'Quezon City',
            'province': 'Metro Manila',
            'lat': 14.640200,
            'lng': 121.048300,
            'contact': '+63 (2) 8928-0611',
            'email': 'trauma.er@eamc.doh.gov.ph',
            'emergency': '+63 (2) 8928-0611 loc 214',
            'beds': 600, 'avail_beds': 58,
            'icu': 40, 'avail_icu': 8,
            'services': ["Emergency & Trauma Care", "Orthopedics & Spine Surgery", "Neurology & Neurosurgery", "General & Laparoscopic Surgery", "Intensive Care Medicine (ICU)", "Oncology & Chemotherapy"],
            'facilities': ["Emergency Department (Level 3)", "Intensive Care Unit (ICU)", "Operating Theatres Suite (4 ORs)", "CT & MRI Imaging Center", "Blood Bank & Diagnostic Pathology"],
        },
        {
            'name': "St. Luke's Medical Center - Global City (SLMC-BGC)",
            'code': 'SLMC-BGC-06',
            'type': Hospital.HospitalType.TERTIARY,
            'address': '32nd Street, Bonifacio Global City',
            'city': 'Taguig',
            'province': 'Metro Manila',
            'lat': 14.553400,
            'lng': 121.047800,
            'contact': '+63 (2) 8789-7700',
            'email': 'patient.care@stlukes.com.ph',
            'emergency': '+63 (2) 8789-7700 loc 1000',
            'beds': 600, 'avail_beds': 75,
            'icu': 50, 'avail_icu': 12,
            'services': ["Cardiology & Cardiac Surgery", "Neurology & Neurosurgery", "Oncology & Chemotherapy", "Orthopedics & Spine Surgery", "Intensive Care Medicine (ICU)", "General & Laparoscopic Surgery"],
            'facilities': ["Cardiac Catheterization Lab", "Intensive Care Unit (ICU)", "CT & MRI Imaging Center", "Operating Theatres Suite (4 ORs)", "Blood Bank & Diagnostic Pathology"],
        },
        {
            'name': 'Makati Medical Center (MMC)',
            'code': 'MMC-MKT-07',
            'type': Hospital.HospitalType.TERTIARY,
            'address': '2 Amorsolo Street, Legaspi Village',
            'city': 'Makati',
            'province': 'Metro Manila',
            'lat': 14.558900,
            'lng': 121.014900,
            'contact': '+63 (2) 8888-8999',
            'email': 'er.triage@makatimed.net.ph',
            'emergency': '+63 (2) 8888-8999 loc 2222',
            'beds': 600, 'avail_beds': 68,
            'icu': 45, 'avail_icu': 10,
            'services': ["Cardiology & Cardiac Surgery", "Emergency & Trauma Care", "Neurology & Neurosurgery", "Oncology & Chemotherapy", "Orthopedics & Spine Surgery", "Intensive Care Medicine (ICU)"],
            'facilities': ["Emergency Department (Level 3)", "Cardiac Catheterization Lab", "Intensive Care Unit (ICU)", "CT & MRI Imaging Center", "Blood Bank & Diagnostic Pathology"],
        },
        {
            'name': 'The Medical City (TMC) - Ortigas',
            'code': 'TMC-ORT-08',
            'type': Hospital.HospitalType.TERTIARY,
            'address': 'Ortigas Avenue',
            'city': 'Pasig',
            'province': 'Metro Manila',
            'lat': 14.589400,
            'lng': 121.069400,
            'contact': '+63 (2) 8988-1000',
            'email': 'triage.desk@themedicalcity.com',
            'emergency': '+63 (2) 8988-1000 loc 110',
            'beds': 800, 'avail_beds': 88,
            'icu': 60, 'avail_icu': 14,
            'services': ["Neurology & Neurosurgery", "Cardiology & Cardiac Surgery", "Orthopedics & Spine Surgery", "Intensive Care Medicine (ICU)", "General & Laparoscopic Surgery", "Oncology & Chemotherapy"],
            'facilities': ["Cardiac Catheterization Lab", "Intensive Care Unit (ICU)", "CT & MRI Imaging Center", "Operating Theatres Suite (4 ORs)"],
        },
        {
            'name': 'Ospital ng Maynila Medical Center (OMMC)',
            'code': 'OMMC-MNL-09',
            'type': Hospital.HospitalType.SECONDARY,
            'address': 'Roxas Boulevard cor. Quirino Avenue, Malate',
            'city': 'Manila',
            'province': 'Metro Manila',
            'lat': 14.566300,
            'lng': 120.985600,
            'contact': '+63 (2) 8524-6061',
            'email': 'referrals@ospitalngmaynila.gov.ph',
            'emergency': '+63 (2) 8524-6061 loc 105',
            'beds': 300, 'avail_beds': 25,
            'icu': 15, 'avail_icu': 2,
            'services': ["Emergency & Trauma Care", "General & Laparoscopic Surgery", "Obstetrics & High-Risk Pregnancy", "Pediatrics & Neonatal Care"],
            'facilities': ["Emergency Department (Level 3)", "Operating Theatres Suite (4 ORs)", "Blood Bank & Diagnostic Pathology"],
        },
        {
            'name': 'Jose R. Reyes Memorial Medical Center (JRRMMC)',
            'code': 'JRRMMC-MNL-10',
            'type': Hospital.HospitalType.TERTIARY,
            'address': 'San Lazaro Compound, Rizal Avenue, Sta. Cruz',
            'city': 'Manila',
            'province': 'Metro Manila',
            'lat': 14.612800,
            'lng': 120.982200,
            'contact': '+63 (2) 8711-9491',
            'email': 'er.admissions@jrrmmc.doh.gov.ph',
            'emergency': '+63 (2) 8711-9491 loc 205',
            'beds': 450, 'avail_beds': 42,
            'icu': 25, 'avail_icu': 5,
            'services': ["Emergency & Trauma Care", "Orthopedics & Spine Surgery", "General & Laparoscopic Surgery", "Intensive Care Medicine (ICU)"],
            'facilities': ["Emergency Department (Level 3)", "Intensive Care Unit (ICU)", "Operating Theatres Suite (4 ORs)", "Blood Bank & Diagnostic Pathology"],
        },
        {
            'name': 'Rizal Medical Center (RMC)',
            'code': 'RMC-PSG-11',
            'type': Hospital.HospitalType.TERTIARY,
            'address': 'Pasig Boulevard',
            'city': 'Pasig',
            'province': 'Metro Manila',
            'lat': 14.569400,
            'lng': 121.063100,
            'contact': '+63 (2) 8865-8400',
            'email': 'referrals@rmc.doh.gov.ph',
            'emergency': '+63 (2) 8865-8400 loc 112',
            'beds': 500, 'avail_beds': 50,
            'icu': 30, 'avail_icu': 6,
            'services': ["Emergency & Trauma Care", "Obstetrics & High-Risk Pregnancy", "Pediatrics & Neonatal Care", "Intensive Care Medicine (ICU)", "General & Laparoscopic Surgery"],
            'facilities': ["Emergency Department (Level 3)", "Intensive Care Unit (ICU)", "Operating Theatres Suite (4 ORs)", "Blood Bank & Diagnostic Pathology"],
        },
        {
            'name': 'Quirino Memorial Medical Center (QMMC)',
            'code': 'QMMC-QC-12',
            'type': Hospital.HospitalType.TERTIARY,
            'address': 'JP Rizal cor. P. Tuazon, Project 4',
            'city': 'Quezon City',
            'province': 'Metro Manila',
            'lat': 14.622800,
            'lng': 121.072200,
            'contact': '+63 (2) 8421-2250',
            'email': 'triage@qmmc.doh.gov.ph',
            'emergency': '+63 (2) 8421-2250 loc 301',
            'beds': 500, 'avail_beds': 48,
            'icu': 32, 'avail_icu': 7,
            'services': ["Emergency & Trauma Care", "Neurology & Neurosurgery", "Orthopedics & Spine Surgery", "Intensive Care Medicine (ICU)"],
            'facilities': ["Emergency Department (Level 3)", "Intensive Care Unit (ICU)", "CT & MRI Imaging Center", "Blood Bank & Diagnostic Pathology"],
        },
        {
            'name': 'Amang Rodriguez Memorial Medical Center (ARMMC)',
            'code': 'ARMMC-MAR-13',
            'type': Hospital.HospitalType.TERTIARY,
            'address': 'Sumulong Highway, Sto. Niño',
            'city': 'Marikina',
            'province': 'Metro Manila',
            'lat': 14.636700,
            'lng': 121.099700,
            'contact': '+63 (2) 8941-5854',
            'email': 'referrals@armmc.doh.gov.ph',
            'emergency': '+63 (2) 8941-5854 loc 119',
            'beds': 300, 'avail_beds': 30,
            'icu': 18, 'avail_icu': 3,
            'services': ["Emergency & Trauma Care", "General & Laparoscopic Surgery", "Obstetrics & High-Risk Pregnancy", "Intensive Care Medicine (ICU)"],
            'facilities': ["Emergency Department (Level 3)", "Intensive Care Unit (ICU)", "Operating Theatres Suite (4 ORs)"],
        },
        {
            'name': 'San Lazaro Hospital (SLH)',
            'code': 'SLH-MNL-14',
            'type': Hospital.HospitalType.SPECIALTY,
            'address': 'Quiricada Street, Sta. Cruz',
            'city': 'Manila',
            'province': 'Metro Manila',
            'lat': 14.614500,
            'lng': 120.983900,
            'contact': '+63 (2) 8732-3776',
            'email': 'triage@slh.doh.gov.ph',
            'emergency': '+63 (2) 8732-3776 loc 101',
            'beds': 500, 'avail_beds': 60,
            'icu': 20, 'avail_icu': 4,
            'services': ["Emergency & Trauma Care", "Intensive Care Medicine (ICU)", "General & Laparoscopic Surgery"],
            'facilities': ["Emergency Department (Level 3)", "Intensive Care Unit (ICU)", "Blood Bank & Diagnostic Pathology"],
        },
        {
            'name': 'Las Piñas General Hospital & Satellite Trauma Center (LPGH-STC)',
            'code': 'LPGH-LP-15',
            'type': Hospital.HospitalType.SECONDARY,
            'address': 'Diego Cera Avenue, Pulang Lupa I',
            'city': 'Las Piñas',
            'province': 'Metro Manila',
            'lat': 14.484200,
            'lng': 120.984700,
            'contact': '+63 (2) 8873-0556',
            'email': 'trauma@lpgh.doh.gov.ph',
            'emergency': '+63 (2) 8873-0556 loc 110',
            'beds': 200, 'avail_beds': 22,
            'icu': 12, 'avail_icu': 2,
            'services': ["Emergency & Trauma Care", "Orthopedics & Spine Surgery", "General & Laparoscopic Surgery"],
            'facilities': ["Emergency Department (Level 3)", "Operating Theatres Suite (4 ORs)"],
        },
        {
            'name': "St. Luke's Medical Center - Quezon City (SLMC-QC)",
            'code': 'SLMC-QC-16',
            'type': Hospital.HospitalType.TERTIARY,
            'address': '279 E. Rodriguez Sr. Avenue, Cathedral Heights',
            'city': 'Quezon City',
            'province': 'Metro Manila',
            'lat': 14.622600,
            'lng': 121.024200,
            'contact': '+63 (2) 8723-0101',
            'email': 'triage.qc@stlukes.com.ph',
            'emergency': '+63 (2) 8723-0101 loc 1234',
            'beds': 650, 'avail_beds': 78,
            'icu': 55, 'avail_icu': 15,
            'services': ["Neurology & Neurosurgery", "Cardiology & Cardiac Surgery", "Intensive Care Medicine (ICU)", "General & Laparoscopic Surgery"],
            'facilities': ["Cardiac Catheterization Lab", "Intensive Care Unit (ICU)", "Operating Theatres Suite (4 ORs)", "CT & MRI Imaging Center"],
        },
        # ============================================================
        # BUKIDNON PROVINCIAL & DISTRICT HOSPITALS (REGION X)
        # ============================================================
        {
            'name': 'Bukidnon Provincial Medical Center (BPMC)',
            'code': 'BPMC-MAL-01',
            'type': Hospital.HospitalType.TERTIARY,
            'address': 'Sayre Highway, Casisang',
            'city': 'Malaybalay City',
            'province': 'Bukidnon',
            'lat': 8.136700,
            'lng': 125.132800,
            'contact': '+63 (88) 813-2550',
            'email': 'referrals@bpmc.bukidnon.gov.ph',
            'emergency': '+63 (88) 813-2550 loc 111',
            'beds': 350, 'avail_beds': 42,
            'icu': 24, 'avail_icu': 5,
            'services': ["Emergency & Trauma Care", "General & Laparoscopic Surgery", "Pediatrics & Neonatal Care", "Obstetrics & High-Risk Pregnancy", "Intensive Care Medicine (ICU)", "Orthopedics & Spine Surgery", "Nephrology & Hemodialysis"],
            'facilities': ["Emergency Department (Level 3)", "Intensive Care Unit (ICU)", "Operating Theatres Suite (4 ORs)", "CT & MRI Imaging Center", "Blood Bank & Diagnostic Pathology"],
        },
        {
            'name': 'Bethel Baptist Hospital',
            'code': 'BBH-MAL-02',
            'type': Hospital.HospitalType.SECONDARY,
            'address': 'Fortich Street, Barangay 4',
            'city': 'Malaybalay City',
            'province': 'Bukidnon',
            'lat': 8.156100,
            'lng': 125.127500,
            'contact': '+63 (88) 813-2708',
            'email': 'admissions@bethelbaptist.ph',
            'emergency': '+63 (88) 813-2708 loc 101',
            'beds': 100, 'avail_beds': 18,
            'icu': 8, 'avail_icu': 2,
            'services': ["General & Laparoscopic Surgery", "Obstetrics & High-Risk Pregnancy", "Pediatrics & Neonatal Care", "Emergency & Trauma Care"],
            'facilities': ["Emergency Department (Level 3)", "Operating Theatres Suite (4 ORs)", "Blood Bank & Diagnostic Pathology"],
        },
        {
            'name': 'Adventist Medical Center - Valencia',
            'code': 'AMCV-VAL-03',
            'type': Hospital.HospitalType.TERTIARY,
            'address': 'Sayre Highway, Poblacion',
            'city': 'Valencia City',
            'province': 'Bukidnon',
            'lat': 7.906900,
            'lng': 125.094500,
            'contact': '+63 (88) 828-2035',
            'email': 'er.intake@amcvalencia.org',
            'emergency': '+63 (88) 828-2035 loc 222',
            'beds': 150, 'avail_beds': 25,
            'icu': 14, 'avail_icu': 4,
            'services': ["Emergency & Trauma Care", "Cardiology & Cardiac Surgery", "Intensive Care Medicine (ICU)", "General & Laparoscopic Surgery", "Nephrology & Hemodialysis", "Obstetrics & High-Risk Pregnancy"],
            'facilities': ["Emergency Department (Level 3)", "Intensive Care Unit (ICU)", "Cardiac Catheterization Lab", "Operating Theatres Suite (4 ORs)", "Blood Bank & Diagnostic Pathology"],
        },
        {
            'name': "Bukidnon Doctor's Hospital",
            'code': 'BDH-VAL-04',
            'type': Hospital.HospitalType.SECONDARY,
            'address': 'Sayre Highway, Hagkol',
            'city': 'Valencia City',
            'province': 'Bukidnon',
            'lat': 7.915000,
            'lng': 125.092000,
            'contact': '+63 (88) 828-3011',
            'email': 'info@bukidnondoctors.ph',
            'emergency': '+63 (88) 828-3011 loc 105',
            'beds': 85, 'avail_beds': 15,
            'icu': 6, 'avail_icu': 2,
            'services': ["General & Laparoscopic Surgery", "Orthopedics & Spine Surgery", "Emergency & Trauma Care"],
            'facilities': ["Emergency Department (Level 3)", "Operating Theatres Suite (4 ORs)"],
        },
        {
            'name': 'Medidas Medical Center',
            'code': 'MMC-VAL-05',
            'type': Hospital.HospitalType.SECONDARY,
            'address': 'Sayre Highway, Poblacion',
            'city': 'Valencia City',
            'province': 'Bukidnon',
            'lat': 7.904200,
            'lng': 125.090500,
            'contact': '+63 (88) 828-1478',
            'email': 'medidas.med@gmail.com',
            'emergency': '+63 (88) 828-1478',
            'beds': 60, 'avail_beds': 12,
            'icu': 4, 'avail_icu': 1,
            'services': ["Emergency & Trauma Care", "General & Laparoscopic Surgery", "Obstetrics & High-Risk Pregnancy"],
            'facilities': ["Emergency Department (Level 3)", "Operating Theatres Suite (4 ORs)"],
        },
        {
            'name': 'Bukidnon Provincial Hospital - Maramag',
            'code': 'BPH-MAR-06',
            'type': Hospital.HospitalType.SECONDARY,
            'address': 'Base Camp, Sayre Highway',
            'city': 'Maramag',
            'province': 'Bukidnon',
            'lat': 7.760200,
            'lng': 125.006400,
            'contact': '+63 (88) 828-5012',
            'email': 'bph.maramag@bukidnon.gov.ph',
            'emergency': '+63 (88) 828-5012 loc 101',
            'beds': 75, 'avail_beds': 14,
            'icu': 4, 'avail_icu': 1,
            'services': ["Emergency & Trauma Care", "General & Laparoscopic Surgery", "Pediatrics & Neonatal Care", "Obstetrics & High-Risk Pregnancy"],
            'facilities': ["Emergency Department (Level 3)", "Operating Theatres Suite (4 ORs)"],
        },
        {
            'name': 'Bukidnon Provincial Hospital - Manolo Fortich',
            'code': 'BPH-MNF-07',
            'type': Hospital.HospitalType.SECONDARY,
            'address': 'Tankulan, Sayre Highway',
            'city': 'Manolo Fortich',
            'province': 'Bukidnon',
            'lat': 8.367000,
            'lng': 124.865000,
            'contact': '+63 (88) 855-2244',
            'email': 'bph.manolofortich@bukidnon.gov.ph',
            'emergency': '+63 (88) 855-2244',
            'beds': 50, 'avail_beds': 10,
            'icu': 4, 'avail_icu': 1,
            'services': ["Emergency & Trauma Care", "General & Laparoscopic Surgery", "Pediatrics & Neonatal Care"],
            'facilities': ["Emergency Department (Level 3)", "Operating Theatres Suite (4 ORs)"],
        },
        {
            'name': 'Bukidnon Provincial Hospital - San Fernando',
            'code': 'BPH-SNF-08',
            'type': Hospital.HospitalType.SECONDARY,
            'address': 'Halapitan',
            'city': 'San Fernando',
            'province': 'Bukidnon',
            'lat': 7.838500,
            'lng': 125.328000,
            'contact': '+63 (917) 554-1234',
            'email': 'bph.sanfernando@bukidnon.gov.ph',
            'emergency': '+63 (917) 554-1234',
            'beds': 25, 'avail_beds': 6,
            'icu': 0, 'avail_icu': 0,
            'services': ["Emergency & Trauma Care", "Obstetrics & High-Risk Pregnancy"],
            'facilities': ["Emergency Department (Level 3)"],
        },
        {
            'name': 'Bukidnon Provincial Hospital - Kalilangan',
            'code': 'BPH-KAL-09',
            'type': Hospital.HospitalType.SECONDARY,
            'address': 'Poblacion',
            'city': 'Kalilangan',
            'province': 'Bukidnon',
            'lat': 7.747200,
            'lng': 124.750500,
            'contact': '+63 (917) 887-2345',
            'email': 'bph.kalilangan@bukidnon.gov.ph',
            'emergency': '+63 (917) 887-2345',
            'beds': 25, 'avail_beds': 5,
            'icu': 0, 'avail_icu': 0,
            'services': ["Emergency & Trauma Care", "General & Laparoscopic Surgery"],
            'facilities': ["Emergency Department (Level 3)"],
        },
        {
            'name': 'Bukidnon Provincial Hospital - Kibawe',
            'code': 'BPH-KIB-10',
            'type': Hospital.HospitalType.SECONDARY,
            'address': 'Natulongan',
            'city': 'Kibawe',
            'province': 'Bukidnon',
            'lat': 7.568300,
            'lng': 124.992200,
            'contact': '+63 (917) 443-8901',
            'email': 'bph.kibawe@bukidnon.gov.ph',
            'emergency': '+63 (917) 443-8901',
            'beds': 25, 'avail_beds': 7,
            'icu': 0, 'avail_icu': 0,
            'services': ["Emergency & Trauma Care", "Obstetrics & High-Risk Pregnancy"],
            'facilities': ["Emergency Department (Level 3)"],
        },
        {
            'name': 'Bukidnon Provincial Hospital - Malitbog',
            'code': 'BPH-MAL-11',
            'type': Hospital.HospitalType.SECONDARY,
            'address': 'Poblacion',
            'city': 'Malitbog',
            'province': 'Bukidnon',
            'lat': 8.531200,
            'lng': 124.882100,
            'contact': '+63 (917) 229-7654',
            'email': 'bph.malitbog@bukidnon.gov.ph',
            'emergency': '+63 (917) 229-7654',
            'beds': 25, 'avail_beds': 8,
            'icu': 0, 'avail_icu': 0,
            'services': ["Emergency & Trauma Care"],
            'facilities': ["Emergency Department (Level 3)"],
        },
        {
            'name': 'Don Carlos Doctors Hospital',
            'code': 'DCDH-DNC-12',
            'type': Hospital.HospitalType.SECONDARY,
            'address': 'Sayre Highway, Poblacion',
            'city': 'Don Carlos',
            'province': 'Bukidnon',
            'lat': 7.683000,
            'lng': 124.998500,
            'contact': '+63 (88) 828-4455',
            'email': 'info@doncarlosdoctors.ph',
            'emergency': '+63 (88) 828-4455',
            'beds': 40, 'avail_beds': 9,
            'icu': 2, 'avail_icu': 1,
            'services': ["Emergency & Trauma Care", "General & Laparoscopic Surgery"],
            'facilities': ["Emergency Department (Level 3)", "Operating Theatres Suite (4 ORs)"],
        },
        {
            'name': 'St. Joseph Southern Bukidnon Hospital',
            'code': 'SJSBH-MAR-13',
            'type': Hospital.HospitalType.SECONDARY,
            'address': 'Sayre Highway, Poblacion',
            'city': 'Maramag',
            'province': 'Bukidnon',
            'lat': 7.758000,
            'lng': 125.010000,
            'contact': '+63 (88) 828-6700',
            'email': 'stjoseph.maramag@gmail.com',
            'emergency': '+63 (88) 828-6700',
            'beds': 35, 'avail_beds': 7,
            'icu': 2, 'avail_icu': 0,
            'services': ["Emergency & Trauma Care", "Pediatrics & Neonatal Care"],
            'facilities': ["Emergency Department (Level 3)"],
        },
        # ============================================================
        # MAJOR MINDANAO REGIONAL APEX & TERTIARY REFERRAL CENTERS
        # ============================================================
        {
            'name': 'Northern Mindanao Medical Center (NMMC)',
            'code': 'NMMC-CDO-14',
            'type': Hospital.HospitalType.APEX_TRAUMA,
            'address': 'Capitol Compound',
            'city': 'Cagayan de Oro City',
            'province': 'Misamis Oriental',
            'lat': 8.484200,
            'lng': 124.646500,
            'contact': '+63 (88) 856-4147',
            'email': 'er.triage@nmmc.doh.gov.ph',
            'emergency': '+63 (88) 856-4147 loc 119',
            'beds': 800, 'avail_beds': 75,
            'icu': 48, 'avail_icu': 10,
            'services': ["Emergency & Trauma Care", "Cardiology & Cardiac Surgery", "Neurology & Neurosurgery", "Orthopedics & Spine Surgery", "Intensive Care Medicine (ICU)", "General & Laparoscopic Surgery", "Nephrology & Hemodialysis", "Pediatrics & Neonatal Care", "Obstetrics & High-Risk Pregnancy", "Oncology & Chemotherapy"],
            'facilities': ["Emergency Department (Level 3)", "Intensive Care Unit (ICU)", "Cardiac Catheterization Lab", "Operating Theatres Suite (4 ORs)", "CT & MRI Imaging Center", "Blood Bank & Diagnostic Pathology"],
        },
        {
            'name': 'Southern Philippines Medical Center (SPMC)',
            'code': 'SPMC-DVO-15',
            'type': Hospital.HospitalType.APEX_TRAUMA,
            'address': 'J.P. Laurel Avenue, Bajada',
            'city': 'Davao City',
            'province': 'Davao del Sur',
            'lat': 7.094500,
            'lng': 125.626500,
            'contact': '+63 (82) 227-2731',
            'email': 'er.admissions@spmc.doh.gov.ph',
            'emergency': '+63 (82) 227-2731 loc 100',
            'beds': 1500, 'avail_beds': 110,
            'icu': 80, 'avail_icu': 14,
            'services': ["Emergency & Trauma Care", "Cardiology & Cardiac Surgery", "Neurology & Neurosurgery", "Orthopedics & Spine Surgery", "Intensive Care Medicine (ICU)", "General & Laparoscopic Surgery", "Nephrology & Hemodialysis", "Pediatrics & Neonatal Care", "Obstetrics & High-Risk Pregnancy", "Oncology & Chemotherapy"],
            'facilities': ["Emergency Department (Level 3)", "Intensive Care Unit (ICU)", "Pediatric ICU (PICU)", "Neonatal ICU (NICU)", "Cardiac Catheterization Lab", "Operating Theatres Suite (4 ORs)", "CT & MRI Imaging Center", "Blood Bank & Diagnostic Pathology"],
        },
        {
            'name': 'JR Borja General Hospital (JRBGH)',
            'code': 'JRBGH-CDO-16',
            'type': Hospital.HospitalType.TERTIARY,
            'address': 'J.V. Seriña St., Carmen',
            'city': 'Cagayan de Oro City',
            'province': 'Misamis Oriental',
            'lat': 8.472000,
            'lng': 124.631000,
            'contact': '+63 (88) 858-3094',
            'email': 'triage@jrbgh.cdo.gov.ph',
            'emergency': '+63 (88) 858-3094 loc 102',
            'beds': 175, 'avail_beds': 25,
            'icu': 12, 'avail_icu': 3,
            'services': ["Emergency & Trauma Care", "General & Laparoscopic Surgery", "Pediatrics & Neonatal Care", "Obstetrics & High-Risk Pregnancy", "Intensive Care Medicine (ICU)"],
            'facilities': ["Emergency Department (Level 3)", "Intensive Care Unit (ICU)", "Operating Theatres Suite (4 ORs)", "Blood Bank & Diagnostic Pathology"],
        },
        {
            'name': 'Davao Regional Medical Center (DRMC)',
            'code': 'DRMC-TAG-17',
            'type': Hospital.HospitalType.TERTIARY,
            'address': 'Apokon',
            'city': 'Tagum City',
            'province': 'Davao del Norte',
            'lat': 7.447800,
            'lng': 125.807800,
            'contact': '+63 (84) 216-9125',
            'email': 'referrals@drmc.doh.gov.ph',
            'emergency': '+63 (84) 216-9125',
            'beds': 600, 'avail_beds': 50,
            'icu': 35, 'avail_icu': 8,
            'services': ["Emergency & Trauma Care", "General & Laparoscopic Surgery", "Neurology & Neurosurgery", "Orthopedics & Spine Surgery", "Intensive Care Medicine (ICU)", "Nephrology & Hemodialysis"],
            'facilities': ["Emergency Department (Level 3)", "Intensive Care Unit (ICU)", "Operating Theatres Suite (4 ORs)", "CT & MRI Imaging Center", "Blood Bank & Diagnostic Pathology"],
        },
        {
            'name': 'Cotabato Regional and Medical Center (CRMC)',
            'code': 'CRMC-COT-18',
            'type': Hospital.HospitalType.TERTIARY,
            'address': 'Sinsuat Avenue',
            'city': 'Cotabato City',
            'province': 'Maguindanao del Norte',
            'lat': 7.218500,
            'lng': 124.241500,
            'contact': '+63 (64) 421-2340',
            'email': 'info@crmc.doh.gov.ph',
            'emergency': '+63 (64) 421-2340',
            'beds': 600, 'avail_beds': 45,
            'icu': 30, 'avail_icu': 6,
            'services': ["Emergency & Trauma Care", "General & Laparoscopic Surgery", "Neurology & Neurosurgery", "Intensive Care Medicine (ICU)", "Obstetrics & High-Risk Pregnancy"],
            'facilities': ["Emergency Department (Level 3)", "Intensive Care Unit (ICU)", "Operating Theatres Suite (4 ORs)", "Blood Bank & Diagnostic Pathology"],
        },
        {
            'name': 'Mayor Hilarion A. Ramiro Sr. Medical Center (MHARSMC)',
            'code': 'MHARS-OZA-19',
            'type': Hospital.HospitalType.TERTIARY,
            'address': 'Manabay',
            'city': 'Ozamiz City',
            'province': 'Misamis Occidental',
            'lat': 8.146500,
            'lng': 123.839200,
            'contact': '+63 (88) 521-0022',
            'email': 'triage@mharmc.doh.gov.ph',
            'emergency': '+63 (88) 521-0022',
            'beds': 500, 'avail_beds': 40,
            'icu': 25, 'avail_icu': 5,
            'services': ["Emergency & Trauma Care", "General & Laparoscopic Surgery", "Intensive Care Medicine (ICU)", "Nephrology & Hemodialysis"],
            'facilities': ["Emergency Department (Level 3)", "Intensive Care Unit (ICU)", "Operating Theatres Suite (4 ORs)", "Blood Bank & Diagnostic Pathology"],
        }
    ]

    hosp_objs = {}
    for h in hospitals_data:
        obj, _ = Hospital.objects.update_or_create(
            hospital_code=h['code'],
            defaults={
                'hospital_name': h['name'],
                'hospital_type': h['type'],
                'address': h['address'],
                'city': h['city'],
                'province': h['province'],
                'latitude': h['lat'],
                'longitude': h['lng'],
                'contact_number': h['contact'],
                'email': h['email'],
                'emergency_contact': h['emergency'],
                'bed_capacity': h['beds'],
                'available_beds': h['avail_beds'],
                'icu_capacity': h['icu'],
                'available_icu_beds': h['avail_icu'],
                'verification_status': Hospital.VerificationStatus.APPROVED,
                'operating_status': Hospital.OperatingStatus.OPERATIONAL,
            }
        )
        s_list = [service_objs[s] for s in h['services'] if s in service_objs]
        f_list = [facility_objs[f] for f in h['facilities'] if f in facility_objs]
        obj.services.set(s_list)
        obj.facilities.set(f_list)
        hosp_objs[h['code']] = obj
    print(f"Created/Updated {len(hosp_objs)} Philippine Hospitals across Metro Manila, Bukidnon, and Mindanao.")

    # 5. Create Realistic User Accounts across all 4 Roles
    h_pgh = hosp_objs['PGH-MNL-01']
    h_phc = hosp_objs['PHC-QC-02']
    h_eamc = hosp_objs['EAMC-QC-05']
    h_slmc = hosp_objs['SLMC-BGC-06']
    h_bpmc = hosp_objs.get('BPMC-MAL-01')
    h_amcv = hosp_objs.get('AMCV-VAL-03')
    h_nmmc = hosp_objs.get('NMMC-CDO-14')
    h_spmc = hosp_objs.get('SPMC-DVO-15')

    users_data = [
        ('admin@carelink.local', 'Platform Administrator', 'AdminPass123!', User.Role.ADMIN, None, 'System Admin (DOH Central)'),
        ('staff.a1@carelink.local', 'Dr. Aris Thorne (PGH Staff A1)', 'StaffPass123!', User.Role.STAFF, h_pgh, 'Chief Medical Officer / ER Intake'),
        ('staff.a2@carelink.local', 'Nurse Sarah Jenkins (PGH Staff A2)', 'StaffPass123!', User.Role.STAFF, h_pgh, 'Triage Referral Coordinator'),
        ('staff.b1@carelink.local', 'Dr. Marcus Vance (PHC Staff B1)', 'StaffPass123!', User.Role.STAFF, h_phc, 'Cardiology Referral Lead'),
        ('staff.b2@carelink.local', 'Dr. Elena Rostova (EAMC Staff B2)', 'StaffPass123!', User.Role.STAFF, h_eamc, 'Trauma ICU Admissions Lead'),
        ('staff.c1@carelink.local', 'Dr. Victor Stone (SLMC Staff C1)', 'StaffPass123!', User.Role.STAFF, h_slmc, 'Neurovascular Director'),
        ('staff.bpmc@carelink.local', 'Dr. Mateo Balane (BPMC Malaybalay)', 'StaffPass123!', User.Role.STAFF, h_bpmc, 'Bukidnon Provincial Medical Director'),
        ('staff.valencia@carelink.local', 'Dr. Ruth Alcantara (AMC Valencia)', 'StaffPass123!', User.Role.STAFF, h_amcv, 'Critical Care & Cardiology Lead'),
        ('staff.nmmc@carelink.local', 'Dr. Gabriel Ocampo (NMMC CDO)', 'StaffPass123!', User.Role.STAFF, h_nmmc, 'Trauma ICU & Neurosurgery Director'),
        ('staff.spmc@carelink.local', 'Dr. Theresa Navarro (SPMC Davao)', 'StaffPass123!', User.Role.STAFF, h_spmc, 'Mindanao Apex Trauma & Resuscitation Lead'),
        ('coordinator@carelink.local', 'David Kim (Regional Coordinator)', 'CoordPass123!', User.Role.COORDINATOR, None, 'Regional Referral Coordinator'),
        ('dispatcher@carelink.local', 'Captain Ray Miller (Dispatch Lead)', 'DispatchPass123!', User.Role.DISPATCHER, None, 'EMS Logistics Dispatcher'),
    ]

    user_objs = {}
    for email, name, pwd, role, hosp, pos in users_data:
        try:
            user = User.objects.get(email=email)
            user.set_password(pwd)
            user.name = name
            user.role = role
            user.hospital = hosp
            user.position = pos
            user.status = User.Status.ACTIVE
            user.save()
        except User.DoesNotExist:
            user = User.objects.create_user(
                email=email,
                name=name,
                password=pwd,
                role=role,
                hospital=hosp,
                position=pos,
                status=User.Status.ACTIVE
            )
        user_objs[email] = user
    print(f"Created/Verified {len(user_objs)} User Accounts.")

    # 6. Create Diverse Sample Patients & Referrals from multiple Philippine Hospitals
    h_ommc = hosp_objs['OMMC-MNL-09']
    h_qmmc = hosp_objs['QMMC-QC-12']
    h_rmc = hosp_objs['RMC-PSG-11']
    h_armmc = hosp_objs['ARMMC-MAR-13']
    h_lpgh = hosp_objs['LPGH-LP-15']
    h_nkti = hosp_objs['NKTI-QC-03']
    h_pcmc = hosp_objs['PCMC-QC-04']
    h_tmc = hosp_objs['TMC-ORT-08']

    referrals_data = [
        # Case 1: Acute STEMI from Manila (Ospital ng Maynila) -> Top match: PGH / MMC / PHC
        {
            'patient_name': 'Juan Dela Cruz', 'age': 58, 'sex': 'MALE', 'cond': 'Acute ST-Elevation Myocardial Infarction (Anteroseptal STEMI)',
            'summary': 'BP: 90/60, HR: 118, RR: 24, Temp: 37.2, SpO2: 92%. Severe crushing retrosternal chest pain of 2 hours duration radiating to left jaw. ECG shows 3mm ST elevation in V1-V4. Emergent primary percutaneous coronary intervention (PCI) required. Origin lacks cardiac cath lab.',
            'from_hosp': h_ommc, 'to_hosp': h_pgh, 'service': service_objs['Cardiology & Cardiac Surgery'],
            'facility': facility_objs['Cardiac Catheterization Lab'], 'urgency': Referral.Urgency.EMERGENCY,
            'status': Referral.Status.SUBMITTED, 'code': 'REF-2026-STEMI01'
        },
        # Case 2: End-Stage Renal Disease from Quezon City (QMMC) -> Top match: NKTI (National Kidney Center in QC)
        {
            'patient_name': 'Maria Santos', 'age': 52, 'sex': 'FEMALE', 'cond': 'End-Stage Renal Disease with Refractory Uremic Encephalopathy & Hyperkalemia',
            'summary': 'BP: 165/100, HR: 96, RR: 22, Temp: 37.0, SpO2: 95%. Known diabetic nephropathy presenting with confusion, uremic frost, K+ 6.8 mmol/L, Creatinine 840 umol/L. Requires emergent continuous renal replacement therapy (CRRT) and nephrology intervention.',
            'from_hosp': h_qmmc, 'to_hosp': h_nkti, 'service': service_objs['Nephrology & Hemodialysis'],
            'facility': facility_objs['Intensive Care Unit (ICU)'], 'urgency': Referral.Urgency.URGENT,
            'status': Referral.Status.SUBMITTED, 'code': 'REF-2026-RENAL02'
        },
        # Case 3: Pediatric Bronchopneumonia from Pasig (Rizal Medical Center) -> Top match: PCMC (Specialty Children\'s in QC)
        {
            'patient_name': 'Baby Angel Dizon', 'age': 2, 'sex': 'FEMALE', 'cond': 'Severe Pediatric Bronchopneumonia with Acute Hypoxemic Respiratory Failure',
            'summary': 'HR: 155, RR: 48, Temp: 38.9, SpO2: 86%. 2-year-old child with severe intercostal and subcostal retractions, grunting, and lethargy. Requires specialized pediatric ICU (PICU) bed and pediatric mechanical ventilation.',
            'from_hosp': h_rmc, 'to_hosp': h_pcmc, 'service': service_objs['Pediatrics & Neonatal Care'],
            'facility': facility_objs['Pediatric ICU (PICU)'], 'urgency': Referral.Urgency.EMERGENCY,
            'status': Referral.Status.SUBMITTED, 'code': 'REF-2026-PED03'
        },
        # Case 4: Severe Traumatic Brain Injury from Manila (Ospital ng Maynila) -> Top match: PGH (Apex Trauma Center in Manila)
        {
            'patient_name': 'Eduardo Reyes', 'age': 29, 'sex': 'MALE', 'cond': 'High-Velocity Motorcycle Collision with Acute Epidural & Subdural Hematoma',
            'summary': 'BP: 140/90, HR: 104, RR: 20, Temp: 37.3, SpO2: 95%. GCS 9 (E2V2M5). Non-contrast cranial CT reveals 12mm left temporoparietal epidural hematoma with 5mm midline shift. Immediate neurosurgical craniotomy and evacuation required.',
            'from_hosp': h_ommc, 'to_hosp': h_pgh, 'service': service_objs['Neurology & Neurosurgery'],
            'facility': facility_objs['Operating Theatres Suite (4 ORs)'], 'urgency': Referral.Urgency.EMERGENCY,
            'status': Referral.Status.SUBMITTED, 'code': 'REF-2026-TRAUMA04'
        },
        # Case 5: Cardiogenic Shock from Quezon City (East Avenue Medical Center) -> Top match: Philippine Heart Center (PHC across East Ave!)
        {
            'patient_name': 'Antonio Luna', 'age': 64, 'sex': 'MALE', 'cond': 'Post-Infarction Cardiogenic Shock requiring Intra-Aortic Balloon Pump (IABP)',
            'summary': 'BP: 80/50, HR: 124, RR: 28, Temp: 36.6, SpO2: 89%. Patient in acute pulmonary edema and severe hypoperfusion following massive inferior myocardial infarction. Requires urgent mechanical circulatory support and cardiac cath lab.',
            'from_hosp': h_eamc, 'to_hosp': h_phc, 'service': service_objs['Cardiology & Cardiac Surgery'],
            'facility': facility_objs['Cardiac Catheterization Lab'], 'urgency': Referral.Urgency.EMERGENCY,
            'status': Referral.Status.SUBMITTED, 'code': 'REF-2026-CARDIAC05'
        },
        # Case 6: Acute Ischemic Stroke from Marikina (Amang Rodriguez) -> Top match: The Medical City Ortigas / St. Luke\'s
        {
            'patient_name': 'Clarissa Tan', 'age': 56, 'sex': 'FEMALE', 'cond': 'Acute Ischemic Stroke with Left MCA Large Vessel Occlusion (LVO)',
            'summary': 'BP: 175/95, HR: 86, RR: 18, Temp: 36.8, SpO2: 97%. Sudden onset right hemiplegia and global aphasia 75 minutes prior. NIHSS 18. Within acute mechanical thrombectomy therapeutic window. Nearest tertiary neurovascular suite required.',
            'from_hosp': h_armmc, 'to_hosp': h_tmc, 'service': service_objs['Neurology & Neurosurgery'],
            'facility': facility_objs['CT & MRI Imaging Center'], 'urgency': Referral.Urgency.EMERGENCY,
            'status': Referral.Status.SUBMITTED, 'code': 'REF-2026-STROKE06'
        },
        # Case 7: Open Femur Fracture from Quezon City (QMMC) -> Top match: East Avenue Medical Center (EAMC Trauma)
        {
            'patient_name': 'Mateo Santos', 'age': 38, 'sex': 'MALE', 'cond': 'Gustilo-Anderson Grade IIIB Open Femoral Shaft Fracture with Soft-Tissue Defect',
            'summary': 'BP: 115/75, HR: 98, RR: 20, Temp: 37.1, SpO2: 98%. Heavy industrial crush injury resulting in comminuted open right femur fracture requiring emergency external fixation and skeletal stabilization.',
            'from_hosp': h_qmmc, 'to_hosp': h_eamc, 'service': service_objs['Orthopedics & Spine Surgery'],
            'facility': facility_objs['Operating Theatres Suite (4 ORs)'], 'urgency': Referral.Urgency.URGENT,
            'status': Referral.Status.SUBMITTED, 'code': 'REF-2026-ORTHO07'
        },
        # Case 8: Active In-Transit Transport (PGH -> PHC) for Telemetry Tracking
        {
            'patient_name': 'Roberto Lim', 'age': 61, 'sex': 'MALE', 'cond': 'Severe Tri-Vessel Coronary Artery Disease for Coronary Artery Bypass Graft (CABG)',
            'summary': 'Transferred for scheduled elective CABG after initial stabilization. In transit with ALS paramedic unit.',
            'from_hosp': h_pgh, 'to_hosp': h_phc, 'service': service_objs['Cardiology & Cardiac Surgery'],
            'facility': facility_objs['Operating Theatres Suite (4 ORs)'], 'urgency': Referral.Urgency.URGENT,
            'status': Referral.Status.DISPATCHED, 'code': 'REF-2026-ACTIVE08'
        },
        # Case 9: Completed Patient Transfer (OMMC -> PGH)
        {
            'patient_name': 'Elena Bautista', 'age': 45, 'sex': 'FEMALE', 'cond': 'Ruptured Ectopic Pregnancy with Hemoperitoneum',
            'summary': 'Successful emergent transfer, bilateral salpingectomy completed at PGH, patient recovered and discharged.',
            'from_hosp': h_ommc, 'to_hosp': h_pgh, 'service': service_objs['Obstetrics & High-Risk Pregnancy'],
            'facility': facility_objs['Operating Theatres Suite (4 ORs)'], 'urgency': Referral.Urgency.EMERGENCY,
            'status': Referral.Status.COMPLETED, 'code': 'REF-2026-DONE09'
        },
        # ============================================================
        # BUKIDNON & MINDANAO CLINICAL REFERRALS
        # ============================================================
        # Case 10: Severe Cranial Trauma from Manolo Fortich (Sayre Highway crash) -> Top: NMMC (CDO Level 3 Apex Trauma)
        {
            'patient_name': 'Joshua Macaslang', 'age': 28, 'sex': 'MALE', 'cond': 'Severe Traumatic Brain Injury & Acute Epidural Hematoma',
            'summary': 'BP: 155/95, HR: 54, RR: 12, Temp: 36.8, SpO2: 95%, GCS: 7 (E2V2M3). High-speed motorcycle crash along Sayre Highway, Tankulan. Cranial CT shows 25mm left temporal acute epidural hematoma with 8mm midline shift. Imminent uncal herniation. Requires emergency craniotomy & neurosurgical evacuation. Origin hospital lacks neurosurgical team.',
            'from_hosp': hosp_objs['BPH-MNF-07'], 'to_hosp': hosp_objs['NMMC-CDO-14'], 'service': service_objs['Neurology & Neurosurgery'],
            'facility': facility_objs['Operating Theatres Suite (4 ORs)'], 'urgency': Referral.Urgency.EMERGENCY,
            'status': Referral.Status.SUBMITTED, 'code': 'REF-2026-BUK-TRAUMA10'
        },
        # Case 11: Acute STEMI from Medidas Medical Center (Valencia City) -> Top: AMC Valencia / NMMC / SPMC
        {
            'patient_name': 'Danilo Salcedo', 'age': 61, 'sex': 'MALE', 'cond': 'Acute Extensive Anterior STEMI with Cardiogenic Shock',
            'summary': 'BP: 85/50, HR: 124, RR: 28, Temp: 36.5, SpO2: 89%. Sustained 3-hour retrosternal crushing pain, diaphoresis. ECG shows tombstone ST elevations across V1-V6. Bilateral pulmonary crackles. Immediate emergency coronary angiogram / primary PCI and cardiac ICU admission required. Inotropic support started.',
            'from_hosp': hosp_objs['MMC-VAL-05'], 'to_hosp': hosp_objs['AMCV-VAL-03'], 'service': service_objs['Cardiology & Cardiac Surgery'],
            'facility': facility_objs['Cardiac Catheterization Lab'], 'urgency': Referral.Urgency.EMERGENCY,
            'status': Referral.Status.SUBMITTED, 'code': 'REF-2026-BUK-STEMI11'
        },
        # Case 12: Pediatric Respiratory Failure from Maramag -> Top: BPMC Malaybalay
        {
            'patient_name': 'Baby John Carl Datu', 'age': 2, 'sex': 'MALE', 'cond': 'Severe Bronchopneumonia with Acute Respiratory Failure',
            'summary': 'BP: 88/54, HR: 168, RR: 64, Temp: 39.4, SpO2: 87% on nasal cannula. Severe intercostal and subcostal retractions, grunting, lethargic. ABG shows severe respiratory acidosis. Requires immediate pediatric intubation, mechanical ventilation, and PICU admission.',
            'from_hosp': hosp_objs['BPH-MAR-06'], 'to_hosp': hosp_objs['BPMC-MAL-01'], 'service': service_objs['Pediatrics & Neonatal Care'],
            'facility': facility_objs['Intensive Care Unit (ICU)'], 'urgency': Referral.Urgency.EMERGENCY,
            'status': Referral.Status.SUBMITTED, 'code': 'REF-2026-BUK-PED12'
        },
        # Case 13: High-Risk Obstructed Labor from San Fernando -> Top: Bethel Baptist Hospital (Malaybalay) / BPMC
        {
            'patient_name': 'Marites Bangcas', 'age': 24, 'sex': 'FEMALE', 'cond': 'G1P0 Pregnancy 39 weeks, Obstructed Labor & Fetal Distress',
            'summary': 'BP: 140/90, HR: 110, RR: 22, Temp: 38.1, SpO2: 98%. Secondary arrest of cervical dilatation at 6cm for 4 hours. Fetal heart rate dips to 80-90 bpm (late decelerations). Meconium-stained amniotic fluid Grade 3. Emergency Cesarean Section indicated immediately.',
            'from_hosp': hosp_objs['BPH-SNF-08'], 'to_hosp': hosp_objs['BBH-MAL-02'], 'service': service_objs['Obstetrics & High-Risk Pregnancy'],
            'facility': facility_objs['Operating Theatres Suite (4 ORs)'], 'urgency': Referral.Urgency.EMERGENCY,
            'status': Referral.Status.SUBMITTED, 'code': 'REF-2026-BUK-OB13'
        },
        # Case 14: Polytrauma / Open Femur from Don Carlos -> Top: BPMC Malaybalay / AMC Valencia
        {
            'patient_name': 'Ramil Okit', 'age': 35, 'sex': 'MALE', 'cond': 'Gustilo-Anderson Grade IIIB Open Femoral Shaft Fracture',
            'summary': 'BP: 95/60, HR: 112, RR: 20, Temp: 37.0, SpO2: 97%. Heavy agricultural machinery rollover. Extensive soft-tissue degloving and protruding bone fragments on right lower extremity. Requires emergency surgical debridement, external fixation, and orthopedic reconstruction.',
            'from_hosp': hosp_objs['DCDH-DNC-12'], 'to_hosp': hosp_objs['BPMC-MAL-01'], 'service': service_objs['Orthopedics & Spine Surgery'],
            'facility': facility_objs['Operating Theatres Suite (4 ORs)'], 'urgency': Referral.Urgency.URGENT,
            'status': Referral.Status.SUBMITTED, 'code': 'REF-2026-BUK-ORTHO14'
        }
    ]

    for r in referrals_data:
        pat, _ = Patient.objects.update_or_create(
            patient_ref_no=f"PAT-{r['code'][-6:]}",
            defaults={
                'name': r['patient_name'],
                'age': r['age'],
                'sex': r['sex'],
                'emergency_status': (r['urgency'] == Referral.Urgency.EMERGENCY),
                'current_condition': r['cond'],
                'clinical_summary': r['summary'],
                'created_by_hospital': r['from_hosp']
            }
        )

        ref, _ = Referral.objects.update_or_create(
            referral_code=r['code'],
            defaults={
                'patient': pat,
                'requesting_hospital': r['from_hosp'],
                'receiving_hospital': r['to_hosp'] if r['status'] != Referral.Status.SUBMITTED else None,
                'required_service': r['service'],
                'required_facility': r['facility'],
                'urgency': r['urgency'],
                'reason_for_referral': f"Specialized {r['service'].name} required beyond local facility capability.",
                'status': r['status'],
                'created_by': user_objs['staff.a1@carelink.local']
            }
        )

        ReferralStatusHistory.objects.get_or_create(
            referral=ref,
            from_status='DRAFT',
            to_status='SUBMITTED',
            defaults={'changed_by': user_objs['staff.a1@carelink.local'], 'notes': 'Initial referral submission.'}
        )

        if r['status'] in [Referral.Status.ACCEPTED, Referral.Status.DISPATCHED, Referral.Status.COMPLETED]:
            transfer_status = Transfer.Status.COMPLETED if r['status'] == Referral.Status.COMPLETED else (
                Transfer.Status.IN_TRANSIT if r['status'] == Referral.Status.DISPATCHED else Transfer.Status.TRANSFER_PENDING
            )
            Transfer.objects.update_or_create(
                referral=ref,
                defaults={
                    'destination_hospital': r['to_hosp'],
                    'dispatcher': user_objs['dispatcher@carelink.local'],
                    'vehicle_number': 'AMB-NCR-104',
                    'vehicle_type': 'ALS Mobile Intensive Care Unit',
                    'driver_name': 'Officer Thomas Wright',
                    'driver_contact': '+63 (917) 555-8899',
                    'paramedic_name': 'Paramedic Jennifer Cole',
                    'pickup_location': f"{r['from_hosp'].hospital_name} Emergency Bay",
                    'status': transfer_status,
                    'handover_notes': 'Patient arrived stable with continuous vital monitoring.' if r['status'] == Referral.Status.COMPLETED else ''
                }
            )

    # 7. Create Audit Log Entry
    AuditLog.objects.create(
        user=user_objs['admin@carelink.local'],
        user_email='admin@carelink.local',
        action='SYSTEM_INITIALIZATION',
        resource='CareLink Platform',
        details='Initial system seed data loaded with 16 Metro Manila Philippine hospitals and diverse clinical triage cases.'
    )

    print(f"Created/Updated {len(referrals_data)} diverse Philippine patient referrals and transfers.")
    print("=" * 60)
    print("Philippine Healthcare Network Seed data loaded successfully!")
    print("=" * 60)

if __name__ == '__main__':
    seed_database()
