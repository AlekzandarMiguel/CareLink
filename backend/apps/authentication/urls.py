from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    CustomTokenObtainPairView, CurrentUserView, UserListCreateView, 
    UserDetailView, ChangePasswordView, SendPasswordResetCodeView, ForgotPasswordResetView
)

urlpatterns = [
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', CurrentUserView.as_view(), name='current_user'),
    path('users/', UserListCreateView.as_view(), name='user_list_create'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user_detail'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('send-reset-code/', SendPasswordResetCodeView.as_view(), name='send_reset_code'),
    path('forgot-password/', ForgotPasswordResetView.as_view(), name='forgot_password'),
]
