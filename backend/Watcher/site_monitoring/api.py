from .models import Site, Alert, Company, TakedownStatus
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from datetime import datetime, timedelta
from .serializers import SiteSerializer, AlertSerializer, MISPSerializer, CompanySerializer
from django.db.models import Q


# Pagination
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


# Company Viewset
class CompanyViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing companies.
    Each user can only see objects related to their company.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanySerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        qs = Company.objects.all().order_by('name')
        return qs


# Site Viewset
class SiteViewSet(viewsets.ModelViewSet):
    permission_classes = [
        permissions.DjangoModelPermissions
    ]
    serializer_class = SiteSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['domain_name', 'ticket_id', 'registrar', 'rtir', 'company__name']
    ordering_fields = ['domain_name', 'created_at', 'legitimacy', 'company__name']

    def get_queryset(self):
        qs = Site.objects.select_related('company').all().order_by('-created_at', '-id')
        
        # Filter by company if provided
        company_id = self.request.query_params.get('company_id', None)
        if company_id:
            qs = qs.filter(company_id=company_id)
        
        # Filter by takedown status
        takedown_status = self.request.query_params.get('takedown_status', None)
        if takedown_status:
            qs = qs.filter(takedown_status=takedown_status)
        
        return qs

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated], url_path='statistics')
    def get_statistics(self, request):
        """
        Get statistics for site monitoring.
        Returns total, malicious, takedown requests, and legal team counts.
        """

        try:
            # Base queryset
            queryset = Site.objects.all()
            
            # Filter by company if provided
            company_id = request.query_params.get('company_id', None)
            if company_id:
                queryset = queryset.filter(company_id=company_id)

            # Total count
            total = queryset.count()

            # Malicious count (legitimacy 5 or 6)
            malicious = queryset.filter(legitimacy__in=[5, 6]).count()

            # Takedown requests (any status except NOT_SUBMITTED)
            takedown_requests = queryset.exclude(takedown_status=TakedownStatus.NOT_SUBMITTED).count()

            # Legal team involvement
            legal_team = queryset.filter(legal_team=True).count()

            stats = {
                'total': total,
                'malicious': malicious,
                'takedownRequests': takedown_requests,
                'legalTeam': legal_team
            }

            return Response(stats, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Failed to calculate statistics: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Alert Viewset
class AlertViewSet(viewsets.ModelViewSet):
    permission_classes = [
        permissions.DjangoModelPermissions
    ]
    serializer_class = AlertSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = Alert.objects.select_related('site__company').order_by('-created_at', '-id')
        
        # Filter by company if provided
        company_id = self.request.query_params.get('company_id', None)
        if company_id:
            qs = qs.filter(site__company_id=company_id)
        
        return qs


class ExportPermission(permissions.DjangoModelPermissions):
    """
    Check for export permission.
    """

    def has_permission(self, request, view):
        return request.user.has_perm('site_monitoring.add_site')


# MISP Viewset
class MISPViewSet(viewsets.ModelViewSet):
    permission_classes = [
        ExportPermission
    ]
    serializer_class = MISPSerializer
