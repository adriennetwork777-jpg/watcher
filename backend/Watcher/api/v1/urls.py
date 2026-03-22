"""
API v1 URLs - Centralized API routing for version 1
"""
from django.urls import path, include

app_name = 'api-v1'

urlpatterns = [
    # Authentication endpoints
    # path('auth/', include('api.v1.views.auth.urls')),
    
    # Data Leak module
    # path('data-leak/', include('api.v1.views.data_leak.urls')),
    
    # DNS Finder module  
    # path('dns-finder/', include('api.v1.views.dns_finder.urls')),
    
    # Site Monitoring module
    # path('site-monitoring/', include('api.v1.views.site_monitoring.urls')),
    
    # Threats Watcher module
    # path('threats-watcher/', include('api.v1.views.threats_watcher.urls')),
    
    # Common endpoints
    # path('common/', include('api.v1.views.common.urls')),
]
