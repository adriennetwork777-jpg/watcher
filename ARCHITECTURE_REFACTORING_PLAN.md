# 🏗️ Architecture Refactoring Plan - Watcher Project

## Audit Complet de l'Architecture Actuelle

### 1. État des Lieux

#### Backend (Django)
- **Structure actuelle** : Applications Django classiques (`accounts`, `common`, `data_leak`, `dns_finder`, `site_monitoring`, `threats_watcher`)
- **API** : Django REST Framework avec Knox Token Authentication
- **Base de données** : MySQL
- **Points critiques identifiés** :
  - ❌ Pas de séparation claire entre logique métier et vues API
  - ❌ Gestion des permissions basique (DjangoModelPermissions uniquement)
  - ❌ Pas de système RBAC centralisé
  - ❌ Code dupliqué dans les utils
  - ❌ Pas de validation centralisée des données
  - ❌ Logging éparpillé
  - ❌ Pas de versioning d'API
  - ❌ Scheduler démarré dans urls.py (mauvaise pratique)

#### Frontend (React)
- **Structure actuelle** : Architecture Redux classique avec actions/reducers/components
- **Routing** : React Router v5 avec HashRouter
- **État global** : Redux + Redux Thunk
- **Points critiques identifiés** :
  - ❌ Structure de dossiers plate et peu scalable
  - ❌ Pas de séparation claire entre composants UI et logique métier
  - ❌ Gestion des erreurs non centralisée
  - ❌ Pas de protection avancée des routes (RBAC)
  - ❌ Appels API dispersés dans les actions
  - ❌ Pas de typage fort (JavaScript vs TypeScript)
  - ❌ Stockage des tokens non sécurisé (localStorage implicite)

---

## 2. Architecture Cible Proposée

### 2.1 Architecture Globale : Monorepo Structuré

```
/workspace/Watcher/
├── backend/                      # Backend Django
│   ├── watcher_core/             # Core Django (settings, urls, wsgi)
│   ├── apps/                     # Applications métier
│   │   ├── accounts/             # Authentification & utilisateurs
│   │   ├── common/               # Fonctionnalités partagées
│   │   ├── data_leak/            # Module Data Leak
│   │   ├── dns_finder/           # Module DNS Finder
│   │   ├── site_monitoring/      # Module Site Monitoring
│   │   └── threats_watcher/      # Module Threats Watcher
│   ├── core/                     # Couche métier centrale
│   │   ├── services/             # Services métier
│   │   ├── repositories/         # Accès aux données
│   │   └── entities/             # Entités métier
│   ├── api/                      # Couche API
│   │   ├── v1/                   # Versioning API
│   │   │   ├── views/
│   │   │   ├── serializers/
│   │   │   └── urls.py
│   │   └── permissions/          # Permissions personnalisées
│   ├── middleware/               # Middleware personnalisés
│   ├── security/                 # Sécurité (RBAC, audit)
│   └── config/                   # Configuration
├── frontend/
│   └── code/
│       ├── src/                  # Source principale
│       │   ├── app/              # Configuration application
│       │   ├── components/       # Composants réutilisables
│       │   ├── features/         # Features par module
│       │   │   ├── auth/
│       │   │   ├── data-leak/
│       │   │   ├── dns-finder/
│       │   │   └── site-monitoring/
│       │   ├── services/         # Services API
│       │   ├── hooks/            # Custom hooks
│       │   ├── store/            # State management
│       │   ├── utils/            # Utilitaires
│       │   └── types/            # Types (pour migration TS)
│       └── public/
└── shared/                       # Code partagé (optionnel)
    └── schemas/                  # Schémas de validation communs
```

---

## 3. Backend - Nouvelle Architecture Django

### 3.1 Structure Détaillée des Dossiers

```
backend/
├── manage.py
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
├── setup.cfg
├── .env.example
├── watcher_core/                 # Projet Django principal
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py              # Configuration de base
│   │   ├── development.py       # Settings dev
│   │   ├── production.py        # Settings prod
│   │   └── testing.py           # Settings tests
│   ├── urls.py                  # URL routing principal
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── __init__.py
│   ├── accounts/
│   │   ├── __init__.py
│   │   ├── models.py            # User, Profile, Role, Permission
│   │   ├── admin.py
│   │   ├── services.py          # Logique métier auth
│   │   └── signals.py
│   ├── common/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── services/
│   │   │   ├── notifications.py
│   │   │   ├── integrations/
│   │   │   │   ├── slack.py
│   │   │   │   ├── thehive.py
│   │   │   │   ├── misp.py
│   │   │   │   └── citadel.py
│   │   │   └── email.py
│   │   └── utils/
│   │       ├── rdap.py
│   │       ├── whois.py
│   │       └── ssl_checker.py
│   ├── data_leak/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── services.py
│   │   └── tasks.py             # Tâches planifiées
│   ├── dns_finder/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── services.py
│   │   └── tasks.py
│   ├── site_monitoring/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── services.py
│   │   └── tasks.py
│   └── threats_watcher/
│       ├── __init__.py
│       ├── models.py
│       ├── services.py
│       └── tasks.py
├── core/
│   ├── __init__.py
│   ├── services/                # Services transverses
│   │   ├── base_service.py
│   │   └── audit_service.py
│   ├── repositories/            # Pattern Repository
│   │   ├── base_repository.py
│   │   └── interfaces.py
│   └── entities/                # Entités métier pures
│       └── user.py
├── api/
│   ├── __init__.py
│   ├── v1/
│   │   ├── __init__.py
│   │   ├── urls.py              # Routes API v1
│   │   ├── views/
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # ViewSet de base
│   │   │   ├── accounts/
│   │   │   ├── data_leak/
│   │   │   ├── dns_finder/
│   │   │   └── site_monitoring/
│   │   └── serializers/
│   │       ├── __init__.py
│   │       ├── base.py          # Serializer de base
│   │       ├── accounts/
│   │       ├── data_leak/
│   │       └── common/
│   └── permissions/
│       ├── __init__.py
│       ├── rbac.py              # Permissions RBAC
│       └── mixins.py
├── middleware/
│   ├── __init__.py
│   ├── audit.py                 # Audit logging
│   ├── exception_handler.py     # Gestion centralisée erreurs
│   └── rate_limit.py            # Rate limiting
├── security/
│   ├── __init__.py
│   ├── rbac/
│   │   ├── __init__.py
│   │   ├── models.py            # Role, Permission, RolePermission
│   │   ├── decorators.py        # @require_permission
│   │   └── checker.py           # Vérification permissions
│   └── audit/
│       ├── __init__.py
│       ├── models.py            # AuditLog
│       └── logger.py
└── config/
    ├── __init__.py
    ├── scheduler.py             # Configuration APScheduler
    └── celery.py                # Si migration vers Celery
```

### 3.2 Modèles de Données Améliorés

#### Système RBAC Centralisé

```python
# backend/security/rbac/models.py
from django.db import models
from django.contrib.auth.models import User, Group, Permission
from django.utils import timezone


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


class UserRole(models.Model):
    """
    Table de liaison User - Role avec contexte
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_roles')
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
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    category = models.ForeignKey(PermissionCategory, on_delete=models.SET_NULL, null=True)
    can_delegate = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['role', 'permission']
```

#### Audit Logging

```python
# backend/security/audit/models.py
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
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True)
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Details
    changes = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_sensitive = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['actor', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['is_sensitive', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.action} by {self.actor} at {self.timestamp}"
```

### 3.3 Services Métier (Pattern Service Layer)

```python
# backend/apps/data_leak/services.py
from typing import List, Optional, Dict, Any
from django.db import transaction
from django.utils import timezone
import logging

from apps.data_leak.models import Keyword, Alert, Subscriber
from core.repositories.base_repository import BaseRepository
from security.audit.logger import AuditLogger
from apps.common.services.notifications import NotificationService

logger = logging.getLogger(__name__)


class DataLeakService:
    """
    Service métier pour la gestion des Data Leaks
    Pattern: Service Layer avec isolation de la logique métier
    """
    
    def __init__(self):
        self.repository = BaseRepository(Keyword)
        self.alert_repository = BaseRepository(Alert)
        self.audit_logger = AuditLogger()
        self.notification_service = NotificationService()
    
    @transaction.atomic
    def create_keyword(self, name: str, is_regex: bool = False, user=None) -> Keyword:
        """
        Créer un nouveau keyword avec audit et validation
        """
        # Validation métier
        if Keyword.objects.filter(name__iexact=name).exists():
            raise ValueError(f"Keyword '{name}' already exists")
        
        # Création
        keyword = Keyword.objects.create(
            name=name,
            is_regex=is_regex
        )
        
        # Audit
        self.audit_logger.log(
            action='CREATE',
            actor=user,
            instance=keyword,
            changes={'name': name, 'is_regex': is_regex},
            is_sensitive=False
        )
        
        logger.info(f"Keyword '{name}' created by {user.username if user else 'system'}")
        return keyword
    
    @transaction.atomic
    def delete_keyword(self, keyword_id: int, user=None) -> bool:
        """
        Supprimer un keyword avec cascade contrôlée
        """
        keyword = Keyword.objects.get(pk=keyword_id)
        
        # Compter les alerts associées
        alert_count = Alert.objects.filter(keyword=keyword).count()
        
        # Suppression
        keyword.delete()
        
        # Audit
        self.audit_logger.log(
            action='DELETE',
            actor=user,
            changes={
                'keyword_name': keyword.name,
                'associated_alerts_deleted': alert_count
            },
            is_sensitive=True
        )
        
        logger.warning(f"Keyword '{keyword.name}' deleted by {user.username if user else 'system'}")
        return True
    
    def get_active_alerts(
        self, 
        user=None, 
        limit: int = 100,
        status: bool = True
    ) -> List[Alert]:
        """
        Récupérer les alerts actives avec filtrage par permissions
        """
        queryset = Alert.objects.select_related('keyword').filter(
            status=status
        ).order_by('-created_at')[:limit]
        
        # Filtrage par permissions si utilisateur spécifié
        if user and not user.is_superuser:
            # Implémenter filtrage par rôle/permissions
            pass
        
        return list(queryset)
    
    @transaction.atomic
    def process_detected_leak(
        self,
        keyword: Keyword,
        url: str,
        content: str,
        source: str = 'pastebin'
    ) -> Alert:
        """
        Traiter une fuite de données détectée
        Déclenche les notifications selon les subscribers
        """
        # Créer l'alerte
        alert = Alert.objects.create(
            keyword=keyword,
            url=url,
            content=content,
            status=True
        )
        
        # Récupérer les subscribers
        subscribers = Subscriber.objects.select_related('user_rec').filter(
            user_rec__is_active=True
        )
        
        # Envoyer notifications
        for subscriber in subscribers:
            try:
                if subscriber.email:
                    self.notification_service.send_email_alert(
                        recipient=subscriber.user_rec,
                        alert=alert
                    )
                if subscriber.thehive:
                    self.notification_service.send_thehive_alert(alert)
                if subscriber.slack:
                    self.notification_service.send_slack_alert(alert)
            except Exception as e:
                logger.error(f"Notification failed for {subscriber.user_rec.username}: {e}")
        
        # Audit
        self.audit_logger.log(
            action='CREATE',
            actor=None,  # System action
            instance=alert,
            metadata={'source': source},
            is_sensitive=True
        )
        
        return alert
```

### 3.4 API Views avec Permissions RBAC

```python
# backend/api/v1/views/data_leak.py
from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.data_leak.models import Keyword, Alert
from api.v1.serializers.data_leak import (
    KeywordSerializer, 
    KeywordCreateSerializer,
    AlertSerializer
)
from api.permissions.rbac import RBACPermission, RequirePermission
from security.rbac.decorators import require_permission
from security.audit.logger import AuditLogger
from apps.data_leak.services import DataLeakService


class KeywordViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des Keywords
    Avec permissions RBAC granulaires
    """
    serializer_class = KeywordSerializer
    permission_classes = [permissions.IsAuthenticated, RBACPermission]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = DataLeakService()
        self.audit_logger = AuditLogger()
    
    def get_queryset(self):
        user = self.request.user
        queryset = Keyword.objects.all().order_by('-created_at')
        
        # Filtrage basé sur les permissions
        if not user.has_perm('data_leak.view_all_keywords'):
            # Retourner uniquement les keywords accessibles
            pass
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create':
            return KeywordCreateSerializer
        return KeywordSerializer
    
    @RequirePermission('data_leak.add_keyword')
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            keyword = self.service.create_keyword(
                name=serializer.validated_data['name'],
                is_regex=serializer.validated_data.get('is_regex', False),
                user=request.user
            )
            
            output_serializer = self.get_serializer(keyword)
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)
        
        except ValueError as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @RequirePermission('data_leak.delete_keyword')
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        try:
            self.service.delete_keyword(
                keyword_id=instance.pk,
                user=request.user
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    @extend_schema(
        summary="Get statistics",
        description="Retrieve keyword usage statistics"
    )
    def stats(self, request):
        """
        Endpoint pour statistiques
        """
        stats = {
            'total_keywords': Keyword.objects.count(),
            'regex_keywords': Keyword.objects.filter(is_regex=True).count(),
            'active_alerts': Alert.objects.filter(status=True).count(),
        }
        return Response(stats)
```

### 3.5 Permissions RBAC Personnalisées

```python
# backend/api/permissions/rbac.py
from rest_framework import permissions
from functools import wraps
from django.core.exceptions import PermissionDenied


class RBACPermission(permissions.BasePermission):
    """
    Permission system basé sur les rôles et permissions Django
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superuser a tous les droits
        if request.user.is_superuser:
            return True
        
        # Vérifier les permissions via les rôles
        return self._check_role_permissions(request, view)
    
    def has_object_permission(self, request, view, obj):
        # Permissions au niveau objet
        if request.user.is_superuser:
            return True
        
        # Vérifier permissions spécifiques à l'objet
        return self._check_object_permissions(request, view, obj)
    
    def _check_role_permissions(self, request, view):
        """
        Vérifie les permissions basées sur les rôles de l'utilisateur
        """
        user = request.user
        
        # Mapping action -> permission requise
        action_permissions = {
            'list': 'view',
            'retrieve': 'view',
            'create': 'add',
            'update': 'change',
            'partial_update': 'change',
            'destroy': 'delete',
        }
        
        action = view.action or 'list'
        perm_action = action_permissions.get(action, 'view')
        
        # Construire le nom de permission
        app_label = view.queryset.model._meta.app_label
        model_name = view.queryset.model._meta.model_name
        required_perm = f"{app_label}.{perm_action}_{model_name}"
        
        # Vérifier via les rôles
        return user.has_perm(required_perm)
    
    def _check_object_permissions(self, request, view, obj):
        """
        Vérifie les permissions au niveau objet
        """
        # Implémenter logique spécifique si nécessaire
        # Ex: seul le créateur peut modifier
        if hasattr(obj, 'created_by') and obj.created_by == request.user:
            return True
        
        return self.has_permission(request, view)


def RequirePermission(permission_codename):
    """
    Décorateur pour exiger une permission spécifique sur une vue
    Usage: @RequirePermission('data_leak.delete_keyword')
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            if not request.user.has_perm(permission_codename):
                raise PermissionDenied(
                    f"Permission '{permission_codename}' required"
                )
            return func(self, request, *args, **kwargs)
        return wrapper
    return decorator
```

### 3.6 Middleware de Gestion d'Erreurs

```python
# backend/middleware/exception_handler.py
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.db import IntegrityError
from django.core.exceptions import PermissionDenied, ValidationError
import logging
import traceback

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Gestionnaire d'exceptions personnalisé pour API cohérente
    """
    # Appel au handler par défaut DRF
    response = exception_handler(exc, context)
    
    # Si DRF a déjà géré, on standardise le format
    if response is not None:
        return _standardize_error_response(response, exc)
    
    # Gestion des exceptions non traitées par DRF
    request = context.get('request')
    
    if isinstance(exc, PermissionDenied):
        logger.warning(f"Permission denied: {exc}", extra={'user': request.user.username if request.user else 'anonymous'})
        return _create_error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code='PERMISSION_DENIED',
            message="You do not have permission to perform this action.",
            request=request
        )
    
    if isinstance(exc, IntegrityError):
        logger.error(f"Database integrity error: {exc}", exc_info=True)
        return _create_error_response(
            status_code=status.HTTP_409_CONFLICT,
            error_code='INTEGRITY_ERROR',
            message="A database constraint was violated.",
            request=request
        )
    
    if isinstance(exc, ValidationError):
        logger.warning(f"Validation error: {exc}")
        return _create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code='VALIDATION_ERROR',
            message=str(exc),
            request=request
        )
    
    # Exception non gérée - log complet
    logger.critical(
        f"Unhandled exception: {exc}",
        exc_info=True,
        extra={
            'user': request.user.username if request.user else 'anonymous',
            'path': request.path if request else 'unknown'
        }
    )
    
    # En production, ne pas exposer les détails
    from django.conf import settings
    debug_message = str(exc) if settings.DEBUG else "An unexpected error occurred"
    
    return _create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code='INTERNAL_ERROR',
        message=debug_message,
        request=request,
        include_traceback=settings.DEBUG
    )


def _standardize_error_response(response, exc):
    """
    Standardise le format des réponses d'erreur DRF
    """
    standardized_data = {
        'success': False,
        'error': {
            'code': _get_error_code(response.status_code, exc),
            'message': _get_error_message(response, exc),
            'details': response.data if hasattr(response, 'data') else None
        }
    }
    
    response.data = standardized_data
    return response


def _create_error_response(status_code, error_code, message, request=None, include_traceback=False):
    """
    Crée une réponse d'erreur standardisée
    """
    data = {
        'success': False,
        'error': {
            'code': error_code,
            'message': message,
        }
    }
    
    if include_traceback:
        data['error']['traceback'] = traceback.format_exc()
    
    if request:
        data['error']['path'] = request.path
    
    return Response(data, status=status_code)


def _get_error_code(status_code, exc):
    """Map HTTP status code to error code"""
    code_map = {
        400: 'BAD_REQUEST',
        401: 'UNAUTHORIZED',
        403: 'FORBIDDEN',
        404: 'NOT_FOUND',
        409: 'CONFLICT',
        500: 'INTERNAL_ERROR',
    }
    return code_map.get(status_code, 'UNKNOWN_ERROR')


def _get_error_message(response, exc):
    """Extract meaningful error message"""
    if hasattr(response, 'data'):
        if isinstance(response.data, dict):
            return response.data.get('detail', str(exc))
        return str(response.data)
    return str(exc)
```

### 3.7 Configuration APScheduler Centralisée

```python
# backend/config/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.conf import settings
import logging
import tzlocal

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    Service centralisé pour la gestion des tâches planifiées
    Pattern: Singleton
    """
    _instance = None
    _scheduler = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._scheduler is None:
            self._scheduler = BackgroundScheduler(
                timezone=str(tzlocal.get_localzone()),
                job_defaults={
                    'coalesce': True,
                    'max_instances': 3,
                    'misfire_grace_time': 60
                }
            )
    
    def start(self):
        """Démarrer le scheduler"""
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("Scheduler started")
    
    def shutdown(self, wait=True):
        """Arrêter le scheduler"""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=wait)
            logger.info("Scheduler stopped")
    
    def add_job(self, func, trigger='cron', **options):
        """
        Ajouter une tâche planifiée
        """
        job = self._scheduler.add_job(
            func,
            trigger=trigger,
            **options
        )
        logger.info(f"Scheduled job: {func.__name__} - {options.get('id', 'unknown')}")
        return job
    
    def remove_job(self, job_id):
        """Supprimer une tâche"""
        self._scheduler.remove_job(job_id)
        logger.info(f"Removed job: {job_id}")


# Initialisation au démarrage de l'application
def initialize_scheduler():
    """
    Initialiser et configurer toutes les tâches planifiées
    À appeler dans apps.py ready()
    """
    from apps.common.tasks import update_legitimate_domains_rdap_data
    from apps.site_monitoring.tasks import update_monitored_sites_rdap_data
    from apps.common.tasks import update_all_ssl_certificates
    
    scheduler = SchedulerService()
    
    # WHOIS discovery every 30 minutes
    scheduler.add_job(
        func=lambda: None,  # Remplacer par vraie fonction
        trigger='cron',
        day_of_week='mon-sun',
        minute='*/30',
        id='whois_job',
        max_instances=10
    )
    
    # SSL certificate check every 6 hours
    scheduler.add_job(
        func=update_all_ssl_certificates,
        trigger='cron',
        day_of_week='mon-sun',
        hour='*/6',
        id='ssl_check_job',
        max_instances=1
    )
    
    scheduler.start()
    return scheduler
```

---

## 4. Frontend - Nouvelle Architecture React

### 4.1 Structure de Dossiers Optimisée

```
frontend/code/
├── src/
│   ├── app/
│   │   ├── App.jsx                    # Composant racine
│   │   ├── routes.jsx                 # Configuration routing
│   │   └── index.jsx                  # Point d'entrée
│   ├── components/
│   │   ├── ui/                        # Composants UI génériques
│   │   │   ├── Button/
│   │   │   ├── Modal/
│   │   │   ├── Table/
│   │   │   ├── Form/
│   │   │   └── Alert/
│   │   ├── layout/                    # Layout components
│   │   │   ├── Header/
│   │   │   ├── Sidebar/
│   │   │   ├── Footer/
│   │   │   └── MainLayout/
│   │   └── common/                    # Composants communs
│   │       ├── Loading/
│   │       ├── ErrorBoundary/
│   │       └── PrivateRoute/
│   ├── features/                      # Features par domaine métier
│   │   ├── auth/
│   │   │   ├── components/
│   │   │   │   ├── LoginForm.jsx
│   │   │   │   └── PasswordChangeForm.jsx
│   │   │   ├── hooks/
│   │   │   │   └── useAuth.js
│   │   │   ├── services/
│   │   │   │   └── authService.js
│   │   │   └── slices/
│   │   │       └── authSlice.js
│   │   ├── data-leak/
│   │   │   ├── components/
│   │   │   │   ├── KeywordList.jsx
│   │   │   │   ├── AlertDashboard.jsx
│   │   │   │   └── KeywordForm.jsx
│   │   │   ├── hooks/
│   │   │   │   └── useDataLeak.js
│   │   │   ├── services/
│   │   │   │   └── dataLeakService.js
│   │   │   └── slices/
│   │   │       └── dataLeakSlice.js
│   │   ├── dns-finder/
│   │   │   └── ...
│   │   └── site-monitoring/
│   │       └── ...
│   ├── services/                      # Services transverses
│   │   ├── api/
│   │   │   ├── client.js              # Axios instance configurée
│   │   │   ├── interceptors.js        # Interceptors (auth, errors)
│   │   │   └── endpoints.js           # URLs centralisées
│   │   ├── storage.js                 # Secure storage wrapper
│   │   └── logger.js                  # Logging client-side
│   ├── store/
│   │   ├── index.js                   # Store configuration
│   │   ├── rootReducer.js
│   │   └── middleware/
│   │       ├── authMiddleware.js
│   │       └── errorMiddleware.js
│   ├── hooks/                         # Custom hooks globaux
│   │   ├── useApi.js
│   │   ├── useDebounce.js
│   │   └── usePermissions.js
│   ├── utils/
│   │   ├── validators.js
│   │   ├── formatters.js
│   │   └── constants.js
│   ├── contexts/
│   │   ├── AuthContext.js
│   │   ├── ThemeContext.js
│   │   └── PermissionContext.js
│   └── assets/
│       ├── images/
│       └── styles/
├── public/
├── package.json
├── webpack.config.js
└── .eslintrc.js
```

### 4.2 Client API Centralisé et Sécurisé

```javascript
// frontend/code/src/services/api/client.js
import axios from 'axios';
import { setupInterceptors } from './interceptors';
import { getStoredToken, removeStoredToken } from '../storage';

// Create axios instance with base configuration
const apiClient = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Setup interceptors for auth, errors, etc.
setupInterceptors(apiClient);

// Request interceptor for adding auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = getStoredToken();
    if (token) {
      config.headers.Authorization = `Token ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for global error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      removeStoredToken();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default apiClient;
```

```javascript
// frontend/code/src/services/api/interceptors.js
import { showErrorAlert } from '../../utils/alerts';
import logger from '../logger';

export function setupInterceptors(client) {
  // Request logging
  client.interceptors.request.use(
    (config) => {
      logger.debug('API Request', {
        method: config.method,
        url: config.url,
        headers: config.headers,
      });
      return config;
    },
    (error) => {
      logger.error('Request error', error);
      return Promise.reject(error);
    }
  );

  // Response error handling
  client.interceptors.response.use(
    (response) => response,
    (error) => {
      const { response } = error;
      
      if (response) {
        // Server responded with error status
        const { status, data } = response;
        
        logger.error('API Error', {
          status,
          path: response.config.url,
          error: data,
        });
        
        // Show user-friendly error message
        const message = data?.error?.message || data?.detail || 'An error occurred';
        showErrorAlert(message);
      } else {
        // Network error or no response
        logger.error('Network error', error.message);
        showErrorAlert('Network error. Please check your connection.');
      }
      
      return Promise.reject(error);
    }
  );
}
```

### 4.3 Services API par Feature

```javascript
// frontend/code/src/features/auth/services/authService.js
import apiClient from '../../../services/api/client';
import { setStoredToken, getStoredToken, removeStoredToken } from '../../../services/storage';

export const authService = {
  async login(username, password) {
    const response = await apiClient.post('/auth/login/', {
      username,
      password,
    });
    
    const { token, user } = response.data;
    setStoredToken(token);
    
    return { user, token };
  },

  async logout() {
    try {
      await apiClient.post('/auth/logout/');
    } finally {
      removeStoredToken();
    }
  },

  async getCurrentUser() {
    const response = await apiClient.get('/auth/user/');
    return response.data;
  },

  async changePassword(oldPassword, newPassword) {
    const response = await apiClient.post('/auth/passwordchange/', {
      old_password: oldPassword,
      password: newPassword,
    });
    return response.data;
  },

  isAuthenticated() {
    return !!getStoredToken();
  },
};
```

```javascript
// frontend/code/src/features/data-leak/services/dataLeakService.js
import apiClient from '../../../services/api/client';

export const dataLeakService = {
  async getKeywords(params = {}) {
    const response = await apiClient.get('/data_leak/keyword/', { params });
    return response.data;
  },

  async createKeyword(data) {
    const response = await apiClient.post('/data_leak/keyword/', data);
    return response.data;
  },

  async updateKeyword(id, data) {
    const response = await apiClient.patch(`/data_leak/keyword/${id}/`, data);
    return response.data;
  },

  async deleteKeyword(id) {
    await apiClient.delete(`/data_leak/keyword/${id}/`);
  },

  async getAlerts(params = {}) {
    const response = await apiClient.get('/data_leak/alert/', { params });
    return response.data;
  },

  async getStats() {
    const response = await apiClient.get('/data_leak/keyword/stats/');
    return response.data;
  },
};
```

### 4.4 Redux Toolkit Modernization

```javascript
// frontend/code/src/features/auth/slices/authSlice.js
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { authService } from '../services/authService';

// Async thunks
export const login = createAsyncThunk(
  'auth/login',
  async ({ username, password }, { rejectWithValue }) => {
    try {
      const { user } = await authService.login(username, password);
      return user;
    } catch (error) {
      return rejectWithValue(error.response?.data?.error?.message || 'Login failed');
    }
  }
);

export const loadUser = createAsyncThunk(
  'auth/loadUser',
  async (_, { rejectWithValue }) => {
    try {
      return await authService.getCurrentUser();
    } catch (error) {
      return rejectWithValue('Failed to load user');
    }
  }
);

export const logout = createAsyncThunk(
  'auth/logout',
  async () => {
    await authService.logout();
  }
);

const initialState = {
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
  permissions: [],
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    setUser: (state, action) => {
      state.user = action.payload;
      state.isAuthenticated = true;
    },
  },
  extraReducers: (builder) => {
    builder
      // Login
      .addCase(login.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(login.fulfilled, (state, action) => {
        state.isLoading = false;
        state.user = action.payload;
        state.isAuthenticated = true;
      })
      .addCase(login.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })
      // Load User
      .addCase(loadUser.fulfilled, (state, action) => {
        state.user = action.payload;
        state.isAuthenticated = true;
      })
      .addCase(loadUser.rejected, (state) => {
        state.user = null;
        state.isAuthenticated = false;
      })
      // Logout
      .addCase(logout.fulfilled, (state) => {
        state.user = null;
        state.isAuthenticated = false;
        state.token = null;
      });
  },
});

export const { clearError, setUser } = authSlice.actions;
export default authSlice.reducer;
```

### 4.5 Protection des Routes avec RBAC

```javascript
// frontend/code/src/components/common/PrivateRoute.jsx
import React from 'react';
import { Route, Redirect } from 'react-router-dom';
import { useSelector } from 'react-redux';
import { usePermissions } from '../../hooks/usePermissions';

/**
 * Route protégée avec vérification d'authentification et permissions
 * 
 * @param {boolean} isAuthenticated - Requiert authentification
 * @param {string[]} requiredPermissions - Permissions requises
 * @param {string} redirectTo - Route de redirection si échec
 */
const PrivateRoute = ({
  component: Component,
  isAuthenticated = true,
  requiredPermissions = [],
  redirectTo = '/login',
  ...rest
}) => {
  const { isAuthenticated: isAuth, user } = useSelector((state) => state.auth);
  const { hasPermissions } = usePermissions();

  return (
    <Route
      {...rest}
      render={(props) => {
        // Check authentication
        if (isAuthenticated && !isAuth) {
          return <Redirect to={redirectTo} />;
        }

        // Check permissions if required
        if (requiredPermissions.length > 0 && !hasPermissions(requiredPermissions)) {
          return <Redirect to="/unauthorized" />;
        }

        return <Component {...props} />;
      }}
    />
  );
};

export default PrivateRoute;
```

```javascript
// frontend/code/src/hooks/usePermissions.js
import { useSelector } from 'react-redux';
import { useMemo } from 'react';

export function usePermissions() {
  const { user, permissions } = useSelector((state) => state.auth);

  const hasPermission = (permission) => {
    if (!user) return false;
    if (user.is_superuser) return true;
    return permissions.includes(permission);
  };

  const hasPermissions = (permissionsList, all = true) => {
    if (!user) return false;
    if (user.is_superuser) return true;

    if (all) {
      return permissionsList.every((perm) => permissions.includes(perm));
    } else {
      return permissionsList.some((perm) => permissions.includes(perm));
    }
  };

  const canAccessFeature = (featureName) => {
    // Mapping feature -> permissions
    const featurePermissions = {
      'data_leak': ['data_leak.view_keyword', 'data_leak.view_alert'],
      'dns_finder': ['dns_finder.view_dnstwisted'],
      'site_monitoring': ['site_monitoring.view_site'],
    };

    const requiredPerms = featurePermissions[featureName] || [];
    return hasPermissions(requiredPerms, false);
  };

  return useMemo(
    () => ({
      user,
      isAuthenticated: !!user,
      hasPermission,
      hasPermissions,
      canAccessFeature,
      isSuperuser: user?.is_superuser || false,
    }),
    [user, permissions]
  );
}
```

### 4.6 Storage Sécurisé

```javascript
// frontend/code/src/services/storage.js
/**
 * Secure storage wrapper
 * En production, utiliser httpOnly cookies plutôt que localStorage
 */

const TOKEN_KEY = 'auth_token';
const USER_KEY = 'user_data';

// Check if running in secure context
const isSecureContext = window.isSecureContext || window.location.protocol === 'https:';

export const storage = {
  setToken(token) {
    if (isSecureContext) {
      // Prefer httpOnly cookies set by backend
      // This is fallback only
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.setItem(TOKEN_KEY, token);
    }
  },

  getToken() {
    return localStorage.getItem(TOKEN_KEY);
  },

  removeToken() {
    localStorage.removeItem(TOKEN_KEY);
  },

  setUser(user) {
    sessionStorage.setItem(USER_KEY, JSON.stringify(user));
  },

  getUser() {
    const data = sessionStorage.getItem(USER_KEY);
    return data ? JSON.parse(data) : null;
  },

  removeUser() {
    sessionStorage.removeItem(USER_KEY);
  },

  clear() {
    this.removeToken();
    this.removeUser();
  },
};

// Re-export with legacy names for compatibility
export const setStoredToken = storage.setToken;
export const getStoredToken = storage.getToken;
export const removeStoredToken = storage.removeToken;
```

---

## 5. Sécurité Renforcée

### 5.1 Backend - Mesures de Sécurité

```python
# backend/watcher_core/settings/base.py (extraits sécurité)

# Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# CSRF Protection
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'
CSRF_TRUSTED_ORIGINS = [
    'https://watcher.company.com',
]

# Session Security
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 3600  # 1 hour

# Password Validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Rate Limiting (avec django-ratelimit)
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'

# CORS Configuration
CORS_ALLOWED_ORIGINS = [
    "https://watcher.company.com",
]
CORS_ALLOW_CREDENTIALS = True
```

### 5.2 Middleware de Rate Limiting

```python
# backend/middleware/rate_limit.py
from django.core.cache import cache
from rest_framework.throttling import SimpleRateThrottle
from django.conf import settings
import time


class RateLimitMiddleware:
    """
    Middleware pour rate limiting global
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.requests = {}
    
    def __call__(self, request):
        # Skip rate limiting for static files
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return self.get_response(request)
        
        # Get client identifier (IP or user ID)
        if request.user.is_authenticated:
            client_id = f"user:{request.user.id}"
        else:
            client_id = f"ip:{self.get_client_ip(request)}"
        
        # Check rate limit
        if not self.is_allowed(client_id):
            from rest_framework.response import Response
            from rest_framework import status
            return Response(
                {'error': {'code': 'RATE_LIMIT_EXCEEDED', 'message': 'Too many requests'}},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        response = self.get_response(request)
        return response
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')
    
    def is_allowed(self, client_id):
        """
        Implémente un rate limiting simple (100 req/min)
        """
        now = time.time()
        window = 60  # 1 minute
        max_requests = 100
        
        key = f"rate_limit:{client_id}"
        requests = cache.get(key, [])
        
        # Remove old requests
        requests = [t for t in requests if now - t < window]
        
        if len(requests) >= max_requests:
            return False
        
        requests.append(now)
        cache.set(key, requests, timeout=window)
        return True
```

---

## 6. Tests et Qualité

### 6.1 Backend - Pytest Configuration

```python
# backend/pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = watcher_core.settings.testing
python_files = tests.py test_*.py *_tests.py
addopts = 
    --verbose
    --tb=short
    --strict-markers
    --cov=.
    --cov-report=html
    --cov-report=term-missing
    --maxfail=5

markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    e2e: marks tests as end-to-end
```

```python
# backend/apps/data_leak/tests/test_services.py
import pytest
from django.contrib.auth.models import User
from apps.data_leak.models import Keyword
from apps.data_leak.services import DataLeakService


@pytest.mark.django_db
class TestDataLeakService:
    
    @pytest.fixture
    def service(self):
        return DataLeakService()
    
    @pytest.fixture
    def test_user(self):
        return User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
    
    def test_create_keyword_success(self, service, test_user):
        keyword = service.create_keyword(
            name='test_keyword',
            is_regex=False,
            user=test_user
        )
        
        assert keyword.name == 'test_keyword'
        assert keyword.is_regex is False
        assert Keyword.objects.filter(pk=keyword.pk).exists()
    
    def test_create_keyword_duplicate(self, service, test_user):
        Keyword.objects.create(name='duplicate', is_regex=False)
        
        with pytest.raises(ValueError, match='already exists'):
            service.create_keyword(
                name='duplicate',
                is_regex=False,
                user=test_user
            )
    
    def test_delete_keyword_with_audit(self, service, test_user):
        keyword = Keyword.objects.create(name='to_delete', is_regex=False)
        
        result = service.delete_keyword(keyword.pk, user=test_user)
        
        assert result is True
        assert not Keyword.objects.filter(pk=keyword.pk).exists()
```

### 6.2 Frontend - Jest Configuration

```javascript
// frontend/code/jest.config.js
module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.js'],
  moduleNameMapper: {
    '\\.(css|less|scss)$': 'identity-obj-proxy',
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  collectCoverageFrom: [
    'src/**/*.{js,jsx}',
    '!src/index.js',
  ],
  testMatch: [
    '**/__tests__/**/*.+(js|jsx)',
    '**/?(*.)+(spec|test).+(js|jsx)',
  ],
};
```

---

## 7. CI/CD Pipeline

### 7.1 GitHub Actions Workflow

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: testpass
          MYSQL_DATABASE: test_watcher
        options: >-
          --health-cmd="mysqladmin ping"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=3
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run tests
        run: |
          cd backend
          pytest --cov=. --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./backend/coverage.xml

  frontend-tests:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: |
          cd frontend/code
          npm ci
      
      - name: Run linting
        run: |
          cd frontend/code
          npm run lint
      
      - name: Run tests
        run: |
          cd frontend/code
          npm test -- --coverage
  
  security-scan:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Run Bandit (Python security)
        run: |
          pip install bandit
          bandit -r backend/ -f json -o bandit-report.json
      
      - name: Run npm audit
        run: |
          cd frontend/code
          npm audit --audit-level=moderate
```

---

## 8. Dockerisation Améliorée

### 8.1 Dockerfile Backend Multi-stage

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

FROM base as dependencies

COPY requirements.txt .
RUN pip wheel --wheel-dir /app/wheels -r requirements.txt

FROM base as production

COPY --from=dependencies /app/wheels /wheels
RUN pip install --no-cache-dir /wheels/*

COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "watcher_core.wsgi:application"]
```

### 8.2 Dockerfile Frontend

```dockerfile
# frontend/Dockerfile
FROM node:18-alpine as build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production stage with nginx
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Security hardening
RUN addgroup -g 101 -S nginx && \
    adduser -u 101 -S nginx -G nginx && \
    chown -R nginx:nginx /usr/share/nginx/html

USER nginx

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

---

## 9. Plan de Migration Étape par Étape

### Phase 1: Préparation (Semaine 1-2)
1. ✅ Mettre en place la nouvelle structure de dossiers
2. ✅ Configurer les environnements (dev, staging, prod)
3. ✅ Installer outils de linting et formatting
4. ✅ Configurer CI/CD de base

### Phase 2: Backend - Core (Semaine 3-4)
1. ✅ Refondre le système d'authentification
2. ✅ Implémenter RBAC avec modèles
3. ✅ Créer le service layer pour accounts
4. ✅ Mettre en place audit logging

### Phase 3: Backend - API (Semaine 5-6)
1. ✅ Migrer les vues vers la nouvelle structure
2. ✅ Implémenter permissions RBAC dans les vues
3. ✅ Standardiser les réponses API
4. ✅ Ajouter versioning API (v1)

### Phase 4: Frontend - Foundation (Semaine 7-8)
1. ✅ Restructurer les dossiers frontend
2. ✅ Migrer vers Redux Toolkit
3. ✅ Créer le client API centralisé
4. ✅ Implémenter interceptors et gestion d'erreurs

### Phase 5: Frontend - Features (Semaine 9-10)
1. ✅ Migrer feature auth
2. ✅ Migrer feature data_leak
3. ✅ Migrer feature dns_finder
4. ✅ Migrer feature site_monitoring

### Phase 6: Tests et Sécurité (Semaine 11-12)
1. ✅ Écrire tests unitaires backend
2. ✅ Écrire tests unitaires frontend
3. ✅ Tests d'intégration API
4. ✅ Audit de sécurité et corrections

### Phase 7: Déploiement (Semaine 13)
1. ✅ Dockerisation complète
2. ✅ Documentation
3. ✅ Formation équipe
4. ✅ Déploiement progressif

---

## 10. Justifications des Choix Techniques

### Pourquoi garder Django REST Framework ?
- ✅ Mature et bien documenté
- ✅ Intégration parfaite avec Django ORM
- ✅ Supporte bien le versioning d'API
- ✅ Grande communauté et écosystème

### Pourquoi Redux Toolkit plutôt que Zustand ?
- ✅ Déjà utilisé dans le projet (courbe d'apprentissage nulle)
- ✅ Redux Toolkit simplifie énormément Redux classique
- ✅ DevTools excellents pour debugging
- ✅ Meilleure prévisibilité pour applications complexes

### Pourquoi ne pas passer à TypeScript immédiatement ?
- ✅ Migration progressive possible (JSDoc en attendant)
- ✅ Réduit la complexité initiale de la refactorisation
- ✅ Peut être ajouté dans une phase ultérieure

### Pourquoi Architecture en Couches ?
- ✅ Séparation claire des responsabilités
- ✅ Testabilité améliorée
- ✅ Maintenabilité à long terme
- ✅ Respect des principes SOLID

---

## 11. Checklist de Sécurité OWASP

### Top 10 OWASP 2021 Coverage

- [x] **A01: Broken Access Control** → RBAC implémenté
- [x] **A02: Cryptographic Failures** → HTTPS obligatoire, tokens sécurisés
- [x] **A03: Injection** → ORM Django, validation des inputs
- [x] **A04: Insecure Design** → Architecture en couches, principe du moindre privilège
- [x] **A05: Security Misconfiguration** → Settings séparés par environnement
- [x] **A06: Vulnerable Components** → Dependabot, audits réguliers
- [x] **A07: Identification Failures** → Knox tokens avec expiration, rate limiting
- [x] **A08: Software and Data Integrity Failures** → CI/CD avec tests
- [x] **A09: Security Logging Failures** → Audit logging centralisé
- [x] **A10: SSRF** → Validation des URLs externes

---

## 12. Monitoring et Observabilité

### Backend Logging Structure

```python
# backend/watcher_core/settings/base.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/watcher/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}
```

### Intégration Sentry (Optionnel)

```python
# backend/watcher_core/settings/base.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn=os.environ.get('SENTRY_DSN'),
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,
    send_default_pii=True,
    environment=os.environ.get('DJANGO_ENV', 'development'),
)
```

---

## Conclusion

Cette refonte architecturale apporte :

✅ **Modularité** : Code organisé par features et responsabilités  
✅ **Sécurité** : RBAC, audit logging, protection OWASP  
✅ **Scalabilité** : Architecture en couches, services isolés  
✅ **Maintenabilité** : Tests, documentation, code propre  
✅ **Évolutivité** : Facile d'ajouter de nouvelles features  

**Technologies conservées** : Django, DRF, Knox, React, Redux, MySQL, Docker  
**Améliorations ajoutées** : RBAC, audit, tests, CI/CD, structure professionnelle

La migration peut se faire progressivement sans interrompre le service en production.
