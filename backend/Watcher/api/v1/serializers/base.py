"""
Base Serializer for API v1
Common serializer functionality and response formatting
"""
from rest_framework import serializers
from collections import OrderedDict


class BaseSerializer(serializers.ModelSerializer):
    """
    Serializer de base avec fonctionnalités communes
    """
    
    # Champs communs en lecture seule
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    
    class Meta:
        abstract = True
    
    def to_representation(self, instance):
        """
        Formater la représentation JSON avec des champs standardisés
        """
        representation = super().to_representation(instance)
        
        # Ajouter les métadonnées si nécessaire
        if self.context.get('include_metadata', False):
            representation['_metadata'] = {
                'model': instance.__class__.__name__,
                'id': instance.pk if hasattr(instance, 'pk') else None
            }
        
        return representation


class StandardResponseSerializer(serializers.Serializer):
    """
    Serializer pour les réponses API standardisées
    Format: { success: bool, data: any, message: str, errors: dict }
    """
    success = serializers.BooleanField(default=True)
    data = serializers.DictField(required=False)
    message = serializers.CharField(required=False)
    errors = serializers.DictField(required=False)
    
    @classmethod
    def success_response(cls, data=None, message="Operation successful"):
        """Créer une réponse de succès standardisée"""
        return cls({
            'success': True,
            'data': data,
            'message': message
        })
    
    @classmethod
    def error_response(cls, errors, message="Operation failed"):
        """Créer une réponse d'erreur standardisée"""
        return cls({
            'success': False,
            'errors': errors,
            'message': message
        })


class PaginatedResponseSerializer(serializers.Serializer):
    """
    Serializer pour les réponses paginées
    """
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = serializers.ListField()
    
    @classmethod
    def from_paginated(cls, paginated_data):
        """Créer une réponse paginée depuis les données DRF"""
        return cls({
            'count': paginated_data.get('count', 0),
            'next': paginated_data.get('next'),
            'previous': paginated_data.get('previous'),
            'results': paginated_data.get('results', [])
        })
