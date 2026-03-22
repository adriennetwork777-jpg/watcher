"""
Custom permissions for DRF views.
Provides fine-grained access control based on RBAC system.
"""
from rest_framework import permissions
from django.core.exceptions import PermissionDenied
from core.models import AuditLog, user_has_role, user_has_permission


class RequirePermission(permissions.BasePermission):
    """
    Custom permission to check if user has a specific permission codename.
    
    Usage:
        permission_classes = [RequirePermission('site_monitoring.add_site')]
    """
    
    def __init__(self, permission_codename):
        self.permission_codename = permission_codename
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superusers have all permissions
        if request.user.is_superuser:
            return True
        
        return user_has_permission(request.user, self.permission_codename)
    
    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class RequireRole(permissions.BasePermission):
    """
    Custom permission to check if user has a specific role.
    
    Usage:
        permission_classes = [RequireRole('admin')]
    """
    
    def __init__(self, role_name):
        self.role_name = role_name
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superusers have all roles
        if request.user.is_superuser:
            return True
        
        return user_has_role(request.user, self.role_name)
    
    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class RequireAnyPermission(permissions.BasePermission):
    """
    Custom permission to check if user has at least one of the specified permissions.
    
    Usage:
        permission_classes = [RequireAnyPermission(['site_monitoring.add_site', 'site_monitoring.change_site'])]
    """
    
    def __init__(self, permission_codenames):
        self.permission_codenames = permission_codenames
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superusers have all permissions
        if request.user.is_superuser:
            return True
        
        return any(user_has_permission(request.user, perm) for perm in self.permission_codenames)
    
    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class RequireAllPermissions(permissions.BasePermission):
    """
    Custom permission to check if user has all of the specified permissions.
    
    Usage:
        permission_classes = [RequireAllPermissions(['site_monitoring.add_site', 'site_monitoring.view_site'])]
    """
    
    def __init__(self, permission_codenames):
        self.permission_codenames = permission_codenames
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superusers have all permissions
        if request.user.is_superuser:
            return True
        
        return all(user_has_permission(request.user, perm) for perm in self.permission_codenames)
    
    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow read access to anyone, but write access only to admins.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Safe methods (GET, HEAD, OPTIONS) are allowed for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write operations require admin role or superuser
        if request.user.is_superuser:
            return True
        
        return user_has_role(request.user, 'admin')
    
    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class AuditLoggingMixin:
    """
    Mixin to add audit logging to DRF views.
    Automatically logs CRUD actions with resource details.
    """
    
    audit_resource_type = None  # Should be set by the using class
    audit_severity_map = {
        'POST': 'INFO',
        'PUT': 'INFO',
        'PATCH': 'INFO',
        'DELETE': 'WARNING',
    }
    
    audit_action_map = {
        'POST': 'CREATE',
        'PUT': 'UPDATE',
        'PATCH': 'UPDATE',
        'DELETE': 'DELETE',
        'GET': 'READ',
    }
    
    def get_audit_resource_name(self, obj):
        """Get human-readable name for the resource. Override in subclasses."""
        return str(obj)
    
    def get_audit_metadata(self, request, obj, action):
        """Get additional metadata for audit log. Override in subclasses."""
        return {}
    
    def perform_create(self, serializer):
        instance = serializer.save()
        
        if self.audit_resource_type and hasattr(self.request, 'user'):
            AuditLog.log_action(
                user=self.request.user,
                action='CREATE',
                resource_type=self.audit_resource_type,
                resource_id=instance.id,
                resource_name=self.get_audit_resource_name(instance),
                description=f'Created {self.audit_resource_type}: {self.get_audit_resource_name(instance)}',
                severity='INFO',
                ip_address=self.get_client_ip(),
                user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
                metadata=self.get_audit_metadata(self.request, instance, 'CREATE')
            )
        
        return instance
    
    def perform_update(self, serializer):
        instance = serializer.save()
        
        if self.audit_resource_type and hasattr(self.request, 'user'):
            AuditLog.log_action(
                user=self.request.user,
                action='UPDATE',
                resource_type=self.audit_resource_type,
                resource_id=instance.id,
                resource_name=self.get_audit_resource_name(instance),
                description=f'Updated {self.audit_resource_type}: {self.get_audit_resource_name(instance)}',
                severity='INFO',
                ip_address=self.get_client_ip(),
                user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
                metadata=self.get_audit_metadata(self.request, instance, 'UPDATE')
            )
        
        return instance
    
    def perform_destroy(self, instance):
        resource_name = self.get_audit_resource_name(instance)
        
        if self.audit_resource_type and hasattr(self.request, 'user'):
            AuditLog.log_action(
                user=self.request.user,
                action='DELETE',
                resource_type=self.audit_resource_type,
                resource_id=instance.id,
                resource_name=resource_name,
                description=f'Deleted {self.audit_resource_type}: {resource_name}',
                severity='WARNING',
                ip_address=self.get_client_ip(),
                user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
                metadata=self.get_audit_metadata(self.request, instance, 'DELETE')
            )
        
        instance.delete()
    
    def get_client_ip(self):
        """Get client IP address from request."""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return self.request.META.get('REMOTE_ADDR')


def require_permission(permission_codename):
    """
    Decorator for view methods to require a specific permission.
    
    Usage:
        @require_permission('site_monitoring.delete_site')
        def destroy(self, request, *args, **kwargs):
            ...
    """
    def decorator(func):
        def wrapper(self, request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied("Authentication required")
            
            if not request.user.is_superuser and not user_has_permission(request.user, permission_codename):
                AuditLog.log_action(
                    user=request.user,
                    action='OTHER',
                    resource_type='Permission',
                    description=f'Unauthorized access attempt to {permission_codename}',
                    severity='WARNING',
                    ip_address=getattr(self, 'get_client_ip', lambda: request.META.get('REMOTE_ADDR'))(),
                    metadata={'permission': permission_codename, 'view': self.__class__.__name__}
                )
                raise PermissionDenied(f"Missing permission: {permission_codename}")
            
            return func(self, request, *args, **kwargs)
        return wrapper
    return decorator
