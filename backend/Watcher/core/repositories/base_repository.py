"""
Base Repository Pattern - Generic data access layer
Provides CRUD operations with audit logging support
"""
from django.db import models, transaction
from django.core.exceptions import ObjectDoesNotExist
from typing import List, Optional, Dict, Any, TypeVar, Generic
from security.audit.logger import AuditLogger

T = TypeVar('T', bound=models.Model)


class BaseRepository(Generic[T]):
    """
    Repository de base pour l'accès aux données
    Pattern: Repository avec isolation de la couche d'accès aux données
    
    Usage:
        class KeywordRepository(BaseRepository[Keyword]):
            def get_by_name(self, name: str) -> Optional[Keyword]:
                return self.get_queryset().filter(name=name).first()
    """
    
    def __init__(self, model_class: type[T]):
        """
        Initialiser le repository avec un modèle Django
        
        Args:
            model_class: Classe du modèle Django
        """
        self.model_class = model_class
        self.objects = model_class.objects
    
    def get_queryset(self):
        """
        Retourner le QuerySet de base
        Peut être override pour ajouter des select_related/prefetch_related
        """
        return self.objects.all()
    
    def get_by_id(self, id: int) -> Optional[T]:
        """
        Récupérer un objet par son ID
        
        Args:
            id: ID de l'objet
        
        Returns:
            L'objet ou None s'il n'existe pas
        """
        try:
            return self.get_queryset().get(pk=id)
        except ObjectDoesNotExist:
            return None
    
    def get_or_404(self, id: int):
        """
        Récupérer un objet par son ID ou lever DoesNotExist
        
        Args:
            id: ID de l'objet
        
        Returns:
            L'objet
        
        Raises:
            ObjectDoesNotExist: Si l'objet n'existe pas
        """
        return self.get_queryset().get(pk=id)
    
    def list_all(
        self, 
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> List[T]:
        """
        Lister tous les objets avec filtrage optionnel
        
        Args:
            filters: Dictionnaire de filtres Django
            order_by: Liste de champs pour le tri
            limit: Nombre maximum de résultats
        
        Returns:
            Liste d'objets
        """
        queryset = self.get_queryset()
        
        if filters:
            queryset = queryset.filter(**filters)
        
        if order_by:
            queryset = queryset.order_by(*order_by)
        
        if limit:
            queryset = queryset[:limit]
        
        return list(queryset)
    
    def create(
        self, 
        data: Dict[str, Any], 
        actor=None, 
        request=None,
        audit: bool = True
    ) -> T:
        """
        Créer un nouvel objet
        
        Args:
            data: Dictionnaire des données à créer
            actor: Utilisateur qui crée l'objet
            request: Requête HTTP (pour audit)
            audit: Activer/désactiver le logging d'audit
        
        Returns:
            L'objet créé
        """
        instance = self.model_class(**data)
        instance.save()
        
        if audit and actor:
            AuditLogger.log_create(
                actor=actor,
                instance=instance,
                request=request
            )
        
        return instance
    
    def update(
        self, 
        instance: T, 
        data: Dict[str, Any],
        actor=None,
        request=None,
        audit: bool = True
    ) -> T:
        """
        Mettre à jour un objet existant
        
        Args:
            instance: Instance à mettre à jour
            data: Dictionnaire des champs à mettre à jour
            actor: Utilisateur qui met à jour
            request: Requête HTTP (pour audit)
            audit: Activer/désactiver le logging d'audit
        
        Returns:
            L'objet mis à jour
        """
        changes = {}
        
        for field_name, new_value in data.items():
            old_value = getattr(instance, field_name)
            if old_value != new_value:
                changes[field_name] = {
                    'old': str(old_value),
                    'new': str(new_value)
                }
                setattr(instance, field_name, new_value)
        
        instance.save()
        
        if audit and actor and changes:
            AuditLogger.log_update(
                actor=actor,
                instance=instance,
                changes=changes,
                request=request
            )
        
        return instance
    
    def delete(
        self, 
        instance: T,
        actor=None,
        request=None,
        audit: bool = True
    ) -> bool:
        """
        Supprimer un objet
        
        Args:
            instance: Instance à supprimer
            actor: Utilisateur qui supprime
            request: Requête HTTP (pour audit)
            audit: Activer/désactiver le logging d'audit
        
        Returns:
            True si supprimé avec succès
        """
        instance_class = instance.__class__
        instance_id = instance.pk
        
        instance.delete()
        
        if audit and actor:
            AuditLogger.log_delete(
                actor=actor,
                instance_class=instance_class,
                instance_id=instance_id,
                request=request
            )
        
        return True
    
    @transaction.atomic
    def bulk_create(
        self, 
        items: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> List[T]:
        """
        Créer plusieurs objets en une seule opération
        
        Args:
            items: Liste de dictionnaires de données
            batch_size: Taille des lots
        
        Returns:
            Liste des objets créés
        """
        instances = [self.model_class(**data) for data in items]
        return self.model_class.objects.bulk_create(
            instances, 
            batch_size=batch_size
        )
    
    @transaction.atomic
    def bulk_update(
        self,
        instances: List[T],
        fields: List[str],
        batch_size: int = 100
    ) -> int:
        """
        Mettre à jour plusieurs objets en une seule opération
        
        Args:
            instances: Liste d'instances à mettre à jour
            fields: Liste des champs à mettre à jour
            batch_size: Taille des lots
        
        Returns:
            Nombre d'objets mis à jour
        """
        return self.model_class.objects.bulk_update(
            instances,
            fields,
            batch_size=batch_size
        )
    
    def exists(self, **filters) -> bool:
        """
        Vérifier si des objets existent avec les filtres donnés
        
        Args:
            **filters: Filtres Django
        
        Returns:
            True si au moins un objet existe
        """
        return self.get_queryset().filter(**filters).exists()
    
    def count(self, **filters) -> int:
        """
        Compter le nombre d'objets avec les filtres donnés
        
        Args:
            **filters: Filtres Django
        
        Returns:
            Nombre d'objets
        """
        return self.get_queryset().filter(**filters).count()
