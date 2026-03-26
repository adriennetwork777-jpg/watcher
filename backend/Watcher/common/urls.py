from rest_framework import routers
from .api import LegitimateDomainViewSet, HealthViewSet
from .core import start_scheduler

router = routers.DefaultRouter()
router.register('api/common/legitimate_domains', LegitimateDomainViewSet, 'legitimate_domains')
router.register('api/health', HealthViewSet, 'health')

urlpatterns = router.urls

start_scheduler()
