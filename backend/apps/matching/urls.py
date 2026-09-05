from django.urls import path
from .views import (
    ReferralMatchingRecommendationsView,
    DraftReferralPreviewRecommendationsView,
    CoordinatorOverrideView,
    CoordinatorOverrideListView,
    ModelRetrainView,
    ModelStatusView
)

urlpatterns = [
    path('referrals/<int:pk>/recommendations/', ReferralMatchingRecommendationsView.as_view(), name='referral-matching-recommendations'),
    path('referrals/<int:pk>/override/', CoordinatorOverrideView.as_view(), name='referral-coordinator-override'),
    path('overrides/', CoordinatorOverrideListView.as_view(), name='coordinator-overrides-list'),
    path('preview/', DraftReferralPreviewRecommendationsView.as_view(), name='matching-draft-preview'),
    path('retrain/', ModelRetrainView.as_view(), name='model-retrain'),
    path('status/', ModelStatusView.as_view(), name='model-status'),
    path('model-status/', ModelStatusView.as_view(), name='matching-model-status'),
]
