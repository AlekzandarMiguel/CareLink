from django.urls import path
from .views import PatientListCreateView, ReferralListCreateView, ReferralDetailView, ReferralTransitionView, ReferralDocumentUploadView, ReferralMessagesView

urlpatterns = [
    path('patients/', PatientListCreateView.as_view(), name='patient_list_create'),
    path('', ReferralListCreateView.as_view(), name='referral_list_create'),
    path('<int:pk>/', ReferralDetailView.as_view(), name='referral_detail'),
    path('<int:pk>/transition/', ReferralTransitionView.as_view(), name='referral_transition'),
    path('<int:pk>/documents/', ReferralDocumentUploadView.as_view(), name='referral_document_upload'),
    path('<int:pk>/messages/', ReferralMessagesView.as_view(), name='referral_messages'),
]
