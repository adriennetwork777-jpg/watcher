from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Core - RBAC & Security'
    
    def ready(self):
        """Initialize core module when Django starts."""
        # Import signals if needed
        pass
