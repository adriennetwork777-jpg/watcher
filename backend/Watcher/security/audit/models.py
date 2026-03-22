"""
Audit Logging Models - Centralized audit trail for all sensitive actions
"""
from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class AuditAction(models.TextChoices):
    CREATE = 'CREATE', 'Create'
    UPDATE = 'UPDATE', 'Update'
    DELETE = 'DELETE', 'Delete'
    LOGIN = 'LOGIN', 'Login'
    LOGOUT = 'LOGOUT', 'Logout'
    PERMISSION_CHANGE = 'PERMISSION_CHANGE', 'Permission Change'
    ROLE_ASSIGNMENT = 'ROLE_ASSIGNMENT', 'Role Assignment'
    DATA_EXPORT = 'DATA_EXPORT', 'Data Export'
    SENSITIVE_ACCESS = 'SENSITIVE_ACCESS', 'Sensitive Access'
    ACCESS_DENIED = 'ACCESS_DENIED', 'Access Denied'
    PASSWORD_CHANGE = 'PASSWORD_CHANGE', 'Password Change'
    CONFIGURATION_CHANGE = 'CONFIGURATION_CHANGE', 'Configuration Change'


class AuditLog(models.Model):
    """
    Journal d'audit centralisé pour toutes les actions sensibles
    """
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    actor = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='audit_logs'
    )
    action = models.CharField(max_length=50, choices=AuditAction.choices)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Generic relation to any model
    content_type = models.ForeignKey(
        ContentType, 
        on_delete=models.SET_NULL, 
        null=True
    )
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Details
    changes = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_sensitive = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=[
            ('SUCCESS', 'Success'),
            ('FAILURE', 'Failure'),
            ('WARNING', 'Warning'),
        ],
        default='SUCCESS'
    )
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'Audit Logs'
        indexes = [
            models.Index(fields=['actor', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['is_sensitive', '-timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        actor_str = self.actor.username if self.actor else 'System'
        return f"{self.action} by {actor_str} at {self.timestamp}"
    
    @classmethod
    def log_action(cls, action, actor=None, instance=None, changes=None, 
                   metadata=None, is_sensitive=False, status='SUCCESS',
                   ip_address=None, user_agent=None):
        """
        Helper method to create audit log entries
        """
        from django.contrib.contenttypes.models import ContentType
        
        if instance:
            content_type = ContentType.objects.get_for_model(instance)
            object_id = instance.pk
        else:
            content_type = None
            object_id = None
        
        return cls.objects.create(
            actor=actor,
            action=action,
            content_type=content_type,
            object_id=object_id,
            changes=changes or {},
            metadata=metadata or {},
            is_sensitive=is_sensitive,
            status=status,
            ip_address=ip_address,
            user_agent=user_agent or ''
        )
