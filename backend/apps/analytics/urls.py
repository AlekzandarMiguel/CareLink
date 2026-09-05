from django.urls import path
from .views import AnalyticsSummaryView, AnalyticsChartsView

urlpatterns = [
    path('summary/', AnalyticsSummaryView.as_view(), name='analytics_summary'),
    path('charts/', AnalyticsChartsView.as_view(), name='analytics_charts'),
]
