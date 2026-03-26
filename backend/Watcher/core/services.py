"""
Base service class for business logic.
All services should inherit from this class to ensure consistency.
"""
from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from Watcher.core.models import AuditLog


class BaseService:
    """
    Base class for all service classes.
    Provides common functionality for transaction management, audit logging, and error handling.
    """
    
    resource_type = None  # Should be overridden by subclasses
    
    def __init__(self, user=None, request=None):
        """
        Initialize service with user and request context.
        
        Args:
            user: Django User instance (optional)
            request: DRF Request instance (optional)
        """
        self.user = user
        self.request = request
    
    def get_user(self):
        """Get the current user from request or direct assignment."""
        if self.user:
            return self.user
        if self.request and hasattr(self.request, 'user'):
            return self.request.user
        return None
    
    def get_ip_address(self):
        """Get client IP address from request."""
        if not self.request:
            return None
        
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return self.request.META.get('REMOTE_ADDR')
    
    def get_user_agent(self):
        """Get user agent string from request."""
        if not self.request:
            return ''
        return self.request.META.get('HTTP_USER_AGENT', '')
    
    @transaction.atomic
    def execute(self, *args, **kwargs):
        """
        Execute the service logic within a database transaction.
        Override this method in subclasses.
        """
        raise NotImplementedError("Subclasses must implement execute()")
    
    def log_audit(self, action, resource_id=None, resource_name='', description='',
                  severity='INFO', metadata=None):
        """
        Log an audit entry.
        
        Args:
            action: Action type (CREATE, READ, UPDATE, DELETE, etc.)
            resource_id: ID of the affected resource
            resource_name: Name/identifier of the resource
            description: Human-readable description
            severity: Severity level (INFO, WARNING, ERROR, CRITICAL)
            metadata: Additional JSON metadata
        """
        user = self.get_user()
        
        if self.resource_type:
            AuditLog.log_action(
                user=user,
                action=action,
                resource_type=self.resource_type,
                resource_id=resource_id,
                resource_name=resource_name,
                description=description,
                severity=severity,
                ip_address=self.get_ip_address(),
                user_agent=self.get_user_agent(),
                metadata=metadata or {}
            )
    
    def validate_permission(self, permission_codename, raise_exception=True):
        """
        Validate if the current user has a specific permission.
        
        Args:
            permission_codename: Permission codename to check
            raise_exception: If True, raise PermissionDenied on failure
            
        Returns:
            Boolean indicating if user has permission
        """
        from Watcher.core.models import user_has_permission
        
        user = self.get_user()
        
        if not user:
            if raise_exception:
                raise PermissionDenied("Authentication required")
            return False
        
        if user.is_superuser:
            return True
        
        has_permission = user_has_permission(user, permission_codename)
        
        if not has_permission and raise_exception:
            self.log_audit(
                action='OTHER',
                description=f'Unauthorized access attempt to {permission_codename}',
                severity='WARNING',
                metadata={'permission': permission_codename}
            )
            raise PermissionDenied(f"Missing permission: {permission_codename}")
        
        return has_permission
    
    def validate_object_permission(self, obj, permission_codename, raise_exception=True):
        """
        Validate if the current user has permission to perform an action on a specific object.
        
        Args:
            obj: Django model instance
            permission_codename: Permission codename to check
            raise_exception: If True, raise PermissionDenied on failure
            
        Returns:
            Boolean indicating if user has permission
        """
        from guardian.shortcuts import get_perms
        
        user = self.get_user()
        
        if not user:
            if raise_exception:
                raise PermissionDenied("Authentication required")
            return False
        
        if user.is_superuser:
            return True
        
        # Check if user has the permission for this specific object
        perms = get_perms(user, obj)
        has_permission = permission_codename in perms
        
        if not has_permission and raise_exception:
            self.log_audit(
                action='OTHER',
                resource_type=obj.__class__.__name__,
                resource_id=obj.id,
                description=f'Unauthorized access attempt to {obj.__class__.__name__} (id={obj.id})',
                severity='WARNING',
                metadata={'permission': permission_codename}
            )
            raise PermissionDenied(f"Missing permission: {permission_codename}")
        
        return has_permission
