from django.urls import path
from .views import TransferListView, TransferDetailView, TransferAssignView, TransferStatusUpdateView

urlpatterns = [
    path('', TransferListView.as_view(), name='transfer_list'),
    path('<int:pk>/', TransferDetailView.as_view(), name='transfer_detail'),
    path('<int:pk>/assign/', TransferAssignView.as_view(), name='transfer_assign'),
    path('<int:pk>/status/', TransferStatusUpdateView.as_view(), name='transfer_status_update'),
]
