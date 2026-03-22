"""
Audit Logger Service - Centralized audit logging functionality
"""
import logging
from django.contrib.contenttypes.models import ContentType
from security.audit.models import AuditLog, AuditAction

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Service pour l'enregistrement centralisé des actions d'audit
    Pattern: Service Layer avec isolation de la logique d'audit
    """
    
    @staticmethod
    def log(action, actor=None, instance=None, changes=None, 
            metadata=None, is_sensitive=False, status='SUCCESS',
            request=None):
        """
        Enregistrer une action dans le journal d'audit
        
        Args:
            action: Type d'action (string ou AuditAction)
            actor: Utilisateur qui effectue l'action
            instance: Instance de l'objet concerné
            changes: Dictionnaire des changements {field: {old, new}}
            metadata: Métadonnées additionnelles
            is_sensitive: Si l'action est sensible
            status: Statut de l'action (SUCCESS, FAILURE, WARNING)
            request: Requête HTTP (pour extraire IP et user-agent)
        
        Returns:
            AuditLog: L'entrée d'audit créée
        """
        ip_address = None
        user_agent = ''
        
        if request:
            ip_address = AuditLogger._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        try:
            audit_log = AuditLog.log_action(
                action=action if isinstance(action, str) else action.value,
                actor=actor,
                instance=instance,
                changes=changes or {},
                metadata=metadata or {},
                is_sensitive=is_sensitive,
                status=status,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            if is_sensitive:
                logger.warning(
                    f"Audit: {action} by {actor.username if actor else 'System'} "
                    f"on {instance.__class__.__name__}:{instance.pk if instance else 'N/A'}"
                )
            else:
                logger.info(
                    f"Audit: {action} by {actor.username if actor else 'System'}"
                )
            
            return audit_log
            
        except Exception as e:
            logger.error(f"Failed to create audit log: {str(e)}")
            # Ne pas lever l'exception pour ne pas bloquer le flux métier
            return None
    
    @staticmethod
    def log_create(actor, instance, request=None):
        """Log a CREATE action"""
        return AuditLogger.log(
            action=AuditAction.CREATE,
            actor=actor,
            instance=instance,
            changes={'created': str(instance)},
            request=request
        )
    
    @staticmethod
    def log_update(actor, instance, changes, request=None):
        """Log an UPDATE action with field changes"""
        return AuditLogger.log(
            action=AuditAction.UPDATE,
            actor=actor,
            instance=instance,
            changes=changes,
            request=request
        )
    
    @staticmethod
    def log_delete(actor, instance_class, instance_id, request=None):
        """Log a DELETE action"""
        return AuditLogger.log(
            action=AuditAction.DELETE,
            actor=actor,
            changes={
                'model': instance_class.__name__,
                'id': instance_id
            },
            request=request
        )
    
    @staticmethod
    def log_login(actor, request=None, status='SUCCESS'):
        """Log a LOGIN action"""
        return AuditLogger.log(
            action=AuditAction.LOGIN,
            actor=actor,
            metadata={'login_attempt': True},
            status=status,
            request=request
        )
    
    @staticmethod
    def log_logout(actor, request=None):
        """Log a LOGOUT action"""
        return AuditLogger.log(
            action=AuditAction.LOGOUT,
            actor=actor,
            request=request
        )
    
    @staticmethod
    def log_permission_change(actor, target_user, permission, granted, request=None):
        """Log a PERMISSION_CHANGE action"""
        return AuditLogger.log(
            action=AuditAction.PERMISSION_CHANGE,
            actor=actor,
            instance=target_user,
            changes={
                'permission': permission.codename,
                'granted': granted
            },
            is_sensitive=True,
            request=request
        )
    
    @staticmethod
    def log_role_assignment(actor, target_user, role, granted, request=None):
        """Log a ROLE_ASSIGNMENT action"""
        return AuditLogger.log(
            action=AuditAction.ROLE_ASSIGNMENT,
            actor=actor,
            instance=target_user,
            changes={
                'role': role.name,
                'granted': granted
            },
            is_sensitive=True,
            request=request
        )
    
    @staticmethod
    def log_access_denied(actor, resource, reason, request=None):
        """Log an ACCESS_DENIED action"""
        return AuditLogger.log(
            action=AuditAction.ACCESS_DENIED,
            actor=actor,
            changes={
                'resource': resource,
                'reason': reason
            },
            status='FAILURE',
            request=request
        )
    
    @staticmethod
    def _get_client_ip(request):
        """Extraire l'adresse IP du client depuis la requête"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
