from rest_framework import routers
from .api import SiteViewSet, AlertViewSet, MISPViewSet, CompanyViewSet, TakedownRequestViewSet
from .core import start_scheduler

router = routers.DefaultRouter()
router.register('api/site_monitoring/company', CompanyViewSet, 'company')
router.register('api/site_monitoring/takedown-request', TakedownRequestViewSet, 'takedown-request')
router.register('api/site_monitoring/site', SiteViewSet, 'site')
router.register('api/site_monitoring/alert', AlertViewSet, 'alert')
router.register('api/site_monitoring/misp', MISPViewSet, 'misp')

urlpatterns = router.urls

start_scheduler()
