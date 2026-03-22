"""
RBAC Models - Role-Based Access Control system.
Provides centralized management of roles, permissions, and user assignments.
"""
from django.db import models
from django.contrib.auth.models import User, Permission
from django.utils import timezone


class Role(models.Model):
    """
    Represents a role that can be assigned to users.
    Roles group permissions together for easier management.
    """
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Role'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.name

    def assign_permissions(self, permissions):
        """Assign multiple permissions to this role."""
        self.permissions.set(permissions)

    @classmethod
    def get_role_by_name(cls, name):
        """Get a role by its name."""
        try:
            return cls.objects.get(name=name)
        except cls.DoesNotExist:
            return None


class PermissionCategory(models.Model):
    """
    Categories for grouping permissions (e.g., 'site_monitoring', 'data_leak', 'dns_finder').
    Helps organize permissions by module or feature.
    """
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Permission Category'
        verbose_name_plural = 'Permission Categories'

    def __str__(self):
        return self.name


class UserRole(models.Model):
    """
    Junction table between Users and Roles.
    Allows assigning multiple roles to a user with optional expiration.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='user_roles')
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_roles'
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ['user', 'role']
        ordering = ['-assigned_at']
        verbose_name = 'User Role'
        verbose_name_plural = 'User Roles'

    def __str__(self):
        return f"{self.user.username} - {self.role.name}"

    def is_expired(self):
        """Check if the role assignment has expired."""
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return False


class AuditLog(models.Model):
    """
    Centralized audit logging for tracking sensitive actions.
    Records who did what, when, and from where.
    """
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('READ', 'Read'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('PASSWORD_CHANGE', 'Password Change'),
        ('PERMISSION_CHANGE', 'Permission Change'),
        ('ROLE_ASSIGNMENT', 'Role Assignment'),
        ('EXPORT', 'Export'),
        ('OTHER', 'Other'),
    ]

    SEVERITY_CHOICES = [
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='INFO')
    resource_type = models.CharField(max_length=100)  # e.g., 'Site', 'Keyword', 'User'
    resource_id = models.IntegerField(null=True, blank=True)
    resource_name = models.CharField(max_length=255, blank=True)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)  # Additional context
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['action']),
        ]

    def __str__(self):
        return f"[{self.severity}] {self.action} by {self.user.username if self.user else 'Anonymous'} - {self.resource_type}"

    @classmethod
    def log_action(cls, user, action, resource_type, resource_id=None, resource_name='',
                   description='', severity='INFO', ip_address=None, user_agent='', metadata=None):
        """
        Create an audit log entry.
        
        Args:
            user: The user performing the action
            action: Action type (CREATE, READ, UPDATE, DELETE, etc.)
            resource_type: Type of resource affected
            resource_id: ID of the resource
            resource_name: Name/identifier of the resource
            description: Human-readable description
            severity: Severity level (INFO, WARNING, ERROR, CRITICAL)
            ip_address: IP address of the request
            user_agent: User agent string
            metadata: Additional JSON metadata
        """
        return cls.objects.create(
            user=user,
            action=action,
            severity=severity,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {}
        )


def get_user_roles(user):
    """
    Get all active roles for a user.
    
    Args:
        user: Django User instance
        
    Returns:
        QuerySet of active Role objects
    """
    return Role.objects.filter(
        user_roles__user=user,
        user_roles__is_active=True,
        is_active=True
    ).exclude(
        user_roles__expires_at__lt=timezone.now()
    )


def get_user_permissions(user):
    """
    Get all permissions for a user through their roles.
    
    Args:
        user: Django User instance
        
    Returns:
        QuerySet of Permission objects
    """
    roles = get_user_roles(user)
    permission_ids = roles.values_list('permissions', flat=True)
    return Permission.objects.filter(id__in=permission_ids).distinct()


def user_has_role(user, role_name):
    """
    Check if a user has a specific role.
    
    Args:
        user: Django User instance
        role_name: Name of the role to check
        
    Returns:
        Boolean indicating if user has the role
    """
    return Role.objects.filter(
        name=role_name,
        user_roles__user=user,
        user_roles__is_active=True,
        is_active=True
    ).exists()


def user_has_permission(user, permission_codename):
    """
    Check if a user has a specific permission.
    
    Args:
        user: Django User instance
        permission_codename: Codename of the permission (e.g., 'add_site')
        
    Returns:
        Boolean indicating if user has the permission
    """
    # Check direct user permissions first
    if user.has_perm(f'accounts.{permission_codename}'):
        return True
    
    # Check role-based permissions
    user_permissions = get_user_permissions(user)
    return user_permissions.filter(codename=permission_codename).exists()
