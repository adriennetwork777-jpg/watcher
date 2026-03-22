"""
RBAC Decorators and Permission Checkers
Permission enforcement utilities for views and services
"""
from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import Permission
from security.rbac.models import Role, UserRole, RolePermission
from security.audit.logger import AuditLogger


def user_has_permission(user, permission_codename):
    """
    Vérifier si un utilisateur a une permission spécifique
    
    Args:
        user: Utilisateur Django
        permission_codename: Code de la permission (ex: 'data_leak.view_keyword')
    
    Returns:
        bool: True si l'utilisateur a la permission
    """
    if not user or not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    # Vérifier les permissions Django standards
    if user.has_perm(permission_codename):
        return True
    
    # Vérifier les permissions via RBAC personnalisé
    try:
        app_label, codename = permission_codename.split('.', 1)
        permission = Permission.objects.get(
            content_type__app_label=app_label,
            codename=codename
        )
        
        # Vérifier via RolePermission
        has_role_permission = RolePermission.objects.filter(
            role__userrole__user=user,
            role__userrole__is_active=True,
            permission=permission
        ).exists()
        
        return has_role_permission
        
    except (ValueError, Permission.DoesNotExist):
        return False


def user_has_role(user, role_name):
    """
    Vérifier si un utilisateur a un rôle spécifique
    
    Args:
        user: Utilisateur Django
        role_name: Nom du rôle
    
    Returns:
        bool: True si l'utilisateur a le rôle
    """
    if not user or not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    return UserRole.objects.filter(
        user=user,
        role__name=role_name,
        is_active=True
    ).exclude(
        expires_at__lt=__import__('django.utils.timezone').utils.timezone.now()
    ).exists()


def user_has_any_role(user, role_names):
    """
    Vérifier si un utilisateur a au moins un des rôles spécifiés
    
    Args:
        user: Utilisateur Django
        role_names: Liste de noms de rôles
    
    Returns:
        bool: True si l'utilisateur a au moins un rôle
    """
    if not user or not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    return UserRole.objects.filter(
        user=user,
        role__name__in=role_names,
        is_active=True
    ).exclude(
        expires_at__lt=__import__('django.utils.timezone').utils.timezone.now()
    ).exists()


def require_permission(permission_codename, login_url=None, raise_exception=False):
    """
    Décorateur pour requérir une permission spécifique sur une vue
    
    Args:
        permission_codename: Code de la permission requise
        login_url: URL de redirection si non authentifié
        raise_exception: Lever PermissionDenied au lieu de rediriger
    
    Usage:
        @require_permission('data_leak.add_keyword')
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            
            if not user.is_authenticated:
                if raise_exception:
                    raise PermissionDenied("Authentication required")
                from django.shortcuts import redirect
                return redirect(login_url or '/login/')
            
            if not user_has_permission(user, permission_codename):
                # Logger le déni d'accès
                AuditLogger.log_access_denied(
                    actor=user,
                    resource=f"{request.path}:{permission_codename}",
                    reason="Missing permission",
                    request=request
                )
                
                if raise_exception:
                    raise PermissionDenied(
                        f"Permission '{permission_codename}' required"
                    )
                from django.shortcuts import render
                return render(request, '403.html', status=403)
            
            return view_func(request, *args, **kwargs)
        
        return _wrapped_view
    return decorator


def require_role(role_name, raise_exception=False):
    """
    Décorateur pour requérir un rôle spécifique sur une vue
    
    Args:
        role_name: Nom du rôle requis
        raise_exception: Lever PermissionDenied au lieu de retourner 403
    
    Usage:
        @require_role('Admin')
        def admin_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            
            if not user.is_authenticated:
                from django.shortcuts import redirect
                return redirect('/login/')
            
            if not user_has_role(user, role_name):
                AuditLogger.log_access_denied(
                    actor=user,
                    resource=f"{request.path}:role:{role_name}",
                    reason="Missing role",
                    request=request
                )
                
                if raise_exception:
                    raise PermissionDenied(f"Role '{role_name}' required")
                from django.shortcuts import render
                return render(request, '403.html', status=403)
            
            return view_func(request, *args, **kwargs)
        
        return _wrapped_view
    return decorator


def require_any_role(role_names, raise_exception=False):
    """
    Décorateur pour requérir au moins un rôle parmi une liste
    
    Args:
        role_names: Liste de noms de rôles
        raise_exception: Lever PermissionDenied au lieu de retourner 403
    
    Usage:
        @require_any_role(['Admin', 'Manager'])
        def management_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            
            if not user.is_authenticated:
                from django.shortcuts import redirect
                return redirect('/login/')
            
            if not user_has_any_role(user, role_names):
                AuditLogger.log_access_denied(
                    actor=user,
                    resource=f"{request.path}:roles:{','.join(role_names)}",
                    reason="Missing required role",
                    request=request
                )
                
                if raise_exception:
                    raise PermissionDenied(
                        f"One of roles {role_names} required"
                    )
                from django.shortcuts import render
                return render(request, '403.html', status=403)
            
            return view_func(request, *args, **kwargs)
        
        return _wrapped_view
    return decorator


class RBACMixin:
    """
    Mixin pour les ViewSets DRF avec vérification RBAC
    """
    required_permission = None
    required_roles = None
    
    def check_permissions(self, request):
        """
        Vérifier les permissions avant d'exécuter la vue
        """
        user = request.user
        
        if not user.is_authenticated:
            self.permission_denied(
                request, 
                message="Authentication required",
                code=401
            )
        
        # Superuser bypass
        if user.is_superuser:
            return
        
        # Vérifier permission spécifique
        if self.required_permission:
            if not user_has_permission(user, self.required_permission):
                AuditLogger.log_access_denied(
                    actor=user,
                    resource=f"{request.path}:{self.required_permission}",
                    reason="Missing permission",
                    request=request
                )
                self.permission_denied(
                    request,
                    message=f"Permission '{self.required_permission}' required",
                    code=403
                )
        
        # Vérifier rôles requis
        if self.required_roles:
            if not user_has_any_role(user, self.required_roles):
                AuditLogger.log_access_denied(
                    actor=user,
                    resource=f"{request.path}:roles:{','.join(self.required_roles)}",
                    reason="Missing required role",
                    request=request
                )
                self.permission_denied(
                    request,
                    message=f"One of roles {self.required_roles} required",
                    code=403
                )
        
        super().check_permissions(request)
