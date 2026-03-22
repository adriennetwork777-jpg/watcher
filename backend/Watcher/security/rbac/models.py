"""
Security RBAC Models - Role-Based Access Control
Centralized permission and role management
"""
from django.db import models
from django.contrib.auth.models import User, Permission
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class Role(models.Model):
    """
    Rôle métier étendant les groupes Django
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=False, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Roles'
    
    def __str__(self):
        return self.name
    
    def get_permissions(self):
        """Get all permissions for this role"""
        return Permission.objects.filter(
            models.Q(role_permissions__role=self) | 
            models.Q(groups__role=self)
        ).distinct()


class UserRole(models.Model):
    """
    Table de liaison User - Role avec contexte
    """
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='user_roles'
    )
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    granted_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='granted_roles',
        limit_choices_to={'is_staff': True}
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'role']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.role.name}"
    
    def is_expired(self):
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def clean(self):
        """Validate role assignment"""
        if self.is_expired():
            raise ValueError("Role assignment has expired")


class PermissionCategory(models.Model):
    """
    Catégorisation des permissions pour une meilleure gestion
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    
    def __str__(self):
        return self.name


class RolePermission(models.Model):
    """
    Permissions spécifiques par rôle (au-delà de Django)
    """
    role = models.ForeignKey(
        Role, 
        on_delete=models.CASCADE, 
        related_name='role_permissions'
    )
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    category = models.ForeignKey(
        PermissionCategory, 
        on_delete=models.SET_NULL, 
        null=True
    )
    can_delegate = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['role', 'permission']
        verbose_name_plural = 'Role Permissions'
    
    def __str__(self):
        return f"{self.role.name} - {self.permission.codename}"
