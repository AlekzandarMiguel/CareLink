from django.urls import path
from .views import HospitalListCreateView, HospitalDetailView, HospitalApprovalView, MedicalServiceListView, FacilityListView, SpecialtyListView

urlpatterns = [
    path('', HospitalListCreateView.as_view(), name='hospital_list_create'),
    path('<int:pk>/', HospitalDetailView.as_view(), name='hospital_detail'),
    path('<int:pk>/approval/', HospitalApprovalView.as_view(), name='hospital_approval'),
    path('services/', MedicalServiceListView.as_view(), name='medical_service_list'),
    path('facilities/', FacilityListView.as_view(), name='facility_list'),
    path('specialties/', SpecialtyListView.as_view(), name='specialty_list'),
]
