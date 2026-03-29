from django.urls import path, include
from django.contrib import admin

urlpatterns = [
    path('', include('Watcher.frontend.urls')),
    path('', include('Watcher.threats_watcher.urls')),
    path('', include('Watcher.data_leak.urls')),
    path('', include('Watcher.site_monitoring.urls')),
    path('', include('Watcher.dns_finder.urls')),
    path('', include('Watcher.accounts.urls')),
    path('', include('Watcher.common.urls')),
    path('admin/doc/', include('django.contrib.admindocs.urls')),
    path('admin/', admin.site.urls),
]
