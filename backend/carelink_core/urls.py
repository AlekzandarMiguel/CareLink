from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView, RedirectView

urlpatterns = [
    # Django Internal Admin (Relocated to avoid collision with CareLink custom admin portal)
    path('django-admin/', admin.site.urls),

    # Web Views - Direct Portal & Clinical Applications
    path('', TemplateView.as_view(template_name='public/landing.html'), name='home'),
    path('hospital-search/', TemplateView.as_view(template_name='public/hospital_search.html'), name='hospital-search'),
    path('login/', TemplateView.as_view(template_name='public/login.html'), name='login'),
    path('register-hospital/', TemplateView.as_view(template_name='public/register_hospital.html'), name='register-hospital'),
    
    # Platform Administrator Pages
    path('admin/', RedirectView.as_view(url='/admin-dashboard/', permanent=False), name='admin-root-redirect'),
    path('admin-dashboard/', TemplateView.as_view(template_name='admin/dashboard.html'), name='admin-dashboard'),
    path('admin/referrals/', TemplateView.as_view(template_name='admin/referrals.html'), name='admin-referrals'),
    path('admin/users/', TemplateView.as_view(template_name='admin/users.html'), name='admin-users'),
    path('admin/approvals/', TemplateView.as_view(template_name='admin/approvals.html'), name='admin-approvals'),
    path('admin/catalogs/', TemplateView.as_view(template_name='admin/catalogs.html'), name='admin-catalogs'),
    path('admin/ai/', TemplateView.as_view(template_name='admin/ai.html'), name='admin-ai'),
    path('admin/settings/', TemplateView.as_view(template_name='admin/settings.html'), name='admin-settings'),
    path('admin/audit/', TemplateView.as_view(template_name='admin/audit.html'), name='admin-audit'),
    
    # Clinical Hospital Staff Pages
    path('staff-dashboard/', TemplateView.as_view(template_name='staff/dashboard.html'), name='staff-dashboard'),
    path('staff/create-referral/', TemplateView.as_view(template_name='staff/create_referral.html'), name='staff-create-referral'),
    path('staff/outgoing/', TemplateView.as_view(template_name='staff/outgoing.html'), name='staff-outgoing'),
    path('staff/incoming/', TemplateView.as_view(template_name='staff/incoming.html'), name='staff-incoming'),
    path('staff/team/', TemplateView.as_view(template_name='staff/team.html'), name='staff-team'),
    path('staff/capacity/', TemplateView.as_view(template_name='staff/capacity.html'), name='staff-capacity'),
    path('staff/settings/', TemplateView.as_view(template_name='staff/settings.html'), name='staff-settings'),
    
    # Regional Triage Coordinator Pages
    path('coordinator-dashboard/', TemplateView.as_view(template_name='coordinator/dashboard.html'), name='coordinator-dashboard'),
    path('coordinator/matcher/', TemplateView.as_view(template_name='coordinator/matcher.html'), name='coordinator-matcher'),
    path('coordinator/emergency/', TemplateView.as_view(template_name='coordinator/emergency.html'), name='coordinator-emergency'),
    path('coordinator/capacity/', TemplateView.as_view(template_name='coordinator/capacity.html'), name='coordinator-capacity'),
    path('coordinator/transfers/', TemplateView.as_view(template_name='coordinator/transfers.html'), name='coordinator-transfers'),
    path('coordinator/history/', TemplateView.as_view(template_name='coordinator/history.html'), name='coordinator-history'),
    path('coordinator/settings/', TemplateView.as_view(template_name='coordinator/settings.html'), name='coordinator-settings'),
    
    # EMS Dispatcher Pages
    path('dispatcher-dashboard/', TemplateView.as_view(template_name='dispatcher/dashboard.html'), name='dispatcher-dashboard'),
    path('dispatcher/in-transit/', TemplateView.as_view(template_name='dispatcher/in_transit.html'), name='dispatcher-in-transit'),
    path('dispatcher/pending/', TemplateView.as_view(template_name='dispatcher/pending.html'), name='dispatcher-pending'),
    path('dispatcher/completed/', TemplateView.as_view(template_name='dispatcher/completed.html'), name='dispatcher-completed'),
    path('dispatcher/settings/', TemplateView.as_view(template_name='dispatcher/settings.html'), name='dispatcher-settings'),
    
    # Shared Clinical Detail View
    path('referrals/<int:pk>/', TemplateView.as_view(template_name='referrals/detail.html'), name='referral-detail-view'),
    path('settings/', RedirectView.as_view(url='/staff/settings/', permanent=False), name='settings-redirect'),

    # REST APIs
    path('api/auth/', include('apps.authentication.urls')),
    path('api/hospitals/', include('apps.hospitals.urls')),
    path('api/referrals/', include('apps.referrals.urls')),
    path('api/matching/', include('apps.matching.urls')),
    path('api/transfers/', include('apps.transfers.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/audit-logs/', include('apps.audit.urls')),
    path('api/analytics/', include('apps.analytics.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
