from .models import Site, Alert, Company, TakedownStatus, TakedownRequest
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from datetime import datetime, timedelta
from .serializers import (
    SiteSerializer, AlertSerializer, MISPSerializer, 
    CompanySerializer, TakedownRequestSerializer, TakedownCreateSerializer
)
from django.db.models import Q


# Pagination
class StandardResultsSetPagination(PageNumberPagination):
    """
    Custom pagination class for API responses.
    Allows clients to request custom page sizes up to 1000.
    """
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


# Company Viewset
class CompanyViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing companies.
    Each user can only see objects related to their company.
    Provides CRUD operations and credit management.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanySerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        """
        Get all companies ordered by name.
        In future, could be restricted to user's company only.
        """
        qs = Company.objects.all().order_by('name')
        return qs


# Takedown Request Viewset
class TakedownRequestViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing takedown requests.
    Supports filtering by company, status, and date ranges.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TakedownRequestSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['site__domain_name', 'company__name', 'external_reference']
    ordering_fields = ['submitted_at', 'status', 'company__name']

    def get_queryset(self):
        """
        Filter takedown requests by company and status.
        Users can only see requests for their company.
        """
        qs = TakedownRequest.objects.select_related(
            'site', 'company', 'submitted_by'
        ).order_by('-submitted_at')
        
        # Filter by company if provided
        company_id = self.request.query_params.get('company_id', None)
        if company_id:
            qs = qs.filter(company_id=company_id)
        
        # Filter by status if provided
        takedown_status = self.request.query_params.get('status', None)
        if takedown_status:
            qs = qs.filter(status=takedown_status)
        
        return qs

    @action(detail=False, methods=['post'], url_path='request-takedown')
    def request_takedown(self, request):
        """
        Submit a new takedown request.
        Requires sufficient credits in the company's account.
        
        Expected payload:
        {
            "site_id": 123,
            "notes": "Optional notes"
        }
        """
        serializer = TakedownCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                # Save with user context
                takedown_request = serializer.save(user=request.user)
                
                # Return success response
                return Response({
                    'status': 'success',
                    'message': 'Takedown request submitted successfully',
                    'data': TakedownRequestSerializer(takedown_request).data
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                return Response({
                    'status': 'error',
                    'message': f'Failed to create takedown request: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='mark-completed')
    def mark_completed(self, request, pk=None):
        """
        Mark a takedown request as completed (taken down).
        Updates both the request and the associated site.
        """
        try:
            takedown_request = self.get_object()
            takedown_request.mark_as_completed()
            
            return Response({
                'status': 'success',
                'message': 'Takedown request marked as completed',
                'data': TakedownRequestSerializer(takedown_request).data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Failed to update takedown request: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='mark-refused')
    def mark_refused(self, request, pk=None):
        """
        Mark a takedown request as refused.
        Optionally accepts notes explaining the refusal.
        """
        try:
            takedown_request = self.get_object()
            notes = request.data.get('notes', '')
            takedown_request.mark_as_refused(notes=notes)
            
            return Response({
                'status': 'success',
                'message': 'Takedown request marked as refused',
                'data': TakedownRequestSerializer(takedown_request).data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Failed to update takedown request: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='statistics')
    def get_statistics(self, request):
        """
        Get statistics for takedown requests.
        Returns counts by status and total.
        """
        try:
            # Base queryset
            queryset = TakedownRequest.objects.all()
            
            # Filter by company if provided
            company_id = request.query_params.get('company_id', None)
            if company_id:
                queryset = queryset.filter(company_id=company_id)
            
            # Count by status
            stats = {
                'total': queryset.count(),
                'not_submitted': queryset.filter(status=TakedownStatus.NOT_SUBMITTED).count(),
                'submitted': queryset.filter(status=TakedownStatus.SUBMITTED).count(),
                'waiting': queryset.filter(status=TakedownStatus.WAITING).count(),
                'refused': queryset.filter(status=TakedownStatus.REFUSED).count(),
                'taken_down': queryset.filter(status=TakedownStatus.TAKEN_DOWN).count(),
            }
            
            return Response(stats, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Failed to calculate statistics: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Site Viewset
class SiteViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing monitored sites.
    Supports filtering by company, takedown status, and legitimacy.
    """
    permission_classes = [
        permissions.DjangoModelPermissions
    ]
    serializer_class = SiteSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['domain_name', 'ticket_id', 'registrar', 'rtir', 'company__name']
    ordering_fields = ['domain_name', 'created_at', 'legitimacy', 'company__name']

    def get_queryset(self):
        """
        Get all sites with optional filtering by company and takedown status.
        Sites are filtered to show only those belonging to the user's company.
        """
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
    """
    API endpoint for managing alerts.
    Alerts are automatically generated when site changes are detected.
    """
    permission_classes = [
        permissions.DjangoModelPermissions
    ]
    serializer_class = AlertSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """
        Get all alerts with optional filtering by company.
        Alerts are filtered to show only those for the user's company.
        """
        qs = Alert.objects.select_related('site__company').order_by('-created_at', '-id')
        
        # Filter by company if provided
        company_id = self.request.query_params.get('company_id', None)
        if company_id:
            qs = qs.filter(site__company_id=company_id)
        
        return qs


class ExportPermission(permissions.DjangoModelPermissions):
    """
    Check for export permission.
    Users need 'add_site' permission to export data.
    """

    def has_permission(self, request, view):
        return request.user.has_perm('site_monitoring.add_site')


# MISP Viewset
class MISPViewSet(viewsets.ModelViewSet):
    """
    API endpoint for MISP event integration.
    Allows creating and updating MISP events for suspicious domains.
    """
    permission_classes = [
        ExportPermission
    ]
    serializer_class = MISPSerializer
