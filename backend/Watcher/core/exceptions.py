"""
Standardized API response formatting and error handling.
Provides consistent response structures across all API endpoints.
"""
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import APIException


class StandardResponse:
    """
    Standardized API response formatter.
    Ensures consistent response structure across all endpoints.
    """
    
    @staticmethod
    def success(data=None, message='Success', status_code=status.HTTP_200_OK, metadata=None):
        """
        Format a success response.
        
        Args:
            data: Response data (dict, list, or object)
            message: Success message
            status_code: HTTP status code
            metadata: Additional metadata
            
        Returns:
            DRF Response object
        """
        response = {
            'success': True,
            'message': message,
            'data': data if data is not None else {}
        }
        
        if metadata:
            response['metadata'] = metadata
        
        return Response(response, status=status_code)
    
    @staticmethod
    def created(data=None, message='Resource created successfully'):
        """Format a 201 Created response."""
        return StandardResponse.success(
            data=data,
            message=message,
            status_code=status.HTTP_201_CREATED
        )
    
    @staticmethod
    def no_content(message='Operation completed successfully'):
        """Format a 204 No Content response."""
        return StandardResponse.success(
            data={},
            message=message,
            status_code=status.HTTP_204_NO_CONTENT
        )
    
    @staticmethod
    def error(message='An error occurred', errors=None, status_code=status.HTTP_400_BAD_REQUEST, metadata=None):
        """
        Format an error response.
        
        Args:
            message: Error message
            errors: List of specific errors
            status_code: HTTP status code
            metadata: Additional metadata
            
        Returns:
            DRF Response object
        """
        response = {
            'success': False,
            'message': message,
            'errors': errors or []
        }
        
        if metadata:
            response['metadata'] = metadata
        
        return Response(response, status=status_code)
    
    @staticmethod
    def validation_error(errors, message='Validation failed'):
        """Format a 400 Validation Error response."""
        if isinstance(errors, dict):
            error_list = [
                {'field': field, 'messages': messages if isinstance(messages, list) else [messages]}
                for field, messages in errors.items()
            ]
        elif isinstance(errors, list):
            error_list = [{'field': 'general', 'messages': errors}]
        else:
            error_list = [{'field': 'general', 'messages': [str(errors)]}]
        
        return StandardResponse.error(
            message=message,
            errors=error_list,
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    @staticmethod
    def unauthorized(message='Authentication required'):
        """Format a 401 Unauthorized response."""
        return StandardResponse.error(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    @staticmethod
    def forbidden(message='You do not have permission to perform this action'):
        """Format a 403 Forbidden response."""
        return StandardResponse.error(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN
        )
    
    @staticmethod
    def not_found(message='Resource not found'):
        """Format a 404 Not Found response."""
        return StandardResponse.error(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    @staticmethod
    def server_error(message='Internal server error', metadata=None):
        """Format a 500 Internal Server Error response."""
        return StandardResponse.error(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            metadata=metadata
        )
    
    @staticmethod
    def paginated(data, paginator, message='Success'):
        """
        Format a paginated response.
        
        Args:
            data: List of items
            paginator: Paginator instance with pagination info
            message: Success message
            
        Returns:
            DRF Response object
        """
        response = {
            'success': True,
            'message': message,
            'data': {
                'items': data,
                'pagination': {
                    'current_page': paginator.page.number,
                    'total_pages': paginator.page.paginator.num_pages,
                    'page_size': paginator.page.paginator.per_page,
                    'total_items': paginator.page.paginator.count,
                    'has_next': paginator.page.has_next(),
                    'has_previous': paginator.page.has_previous(),
                    'next_page': paginator.page.next_page_number() if paginator.page.has_next() else None,
                    'previous_page': paginator.page.previous_page_number() if paginator.page.has_previous() else None,
                }
            }
        }
        
        return Response(response, status=status.HTTP_200_OK)


class APIError(APIException):
    """
    Custom API exception with standardized error formatting.
    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = 'An unexpected error occurred'
    default_code = 'server_error'
    
    def __init__(self, detail=None, code=None, errors=None, metadata=None):
        """
        Initialize API error.
        
        Args:
            detail: Error message
            code: Error code
            errors: List of specific errors
            metadata: Additional metadata
        """
        super().__init__(detail=detail, code=code)
        self.errors = errors or []
        self.metadata = metadata or {}
    
    def get_response(self):
        """Get formatted error response."""
        return StandardResponse.error(
            message=str(self.detail),
            errors=self.errors,
            status_code=self.status_code,
            metadata=self.metadata
        )


class ValidationError(APIError):
    """Validation error exception."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Validation failed'
    default_code = 'validation_error'


class UnauthorizedError(APIError):
    """Unauthorized error exception."""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = 'Authentication required'
    default_code = 'unauthorized'


class ForbiddenError(APIError):
    """Forbidden error exception."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'You do not have permission to perform this action'
    default_code = 'forbidden'


class NotFoundError(APIError):
    """Not found error exception."""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'Resource not found'
    default_code = 'not_found'


class ConflictError(APIError):
    """Conflict error exception (e.g., duplicate resource)."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'Resource conflict'
    default_code = 'conflict'


def handle_exception(exc):
    """
    Global exception handler for consistent error responses.
    
    Usage:
        Add to REST_FRAMEWORK settings:
        'EXCEPTION_HANDLER': 'core.exceptions.handle_exception'
    """
    from rest_framework.views import exception_handler
    
    # Call REST framework's default exception handler first
    response = exception_handler(exc, {})
    
    if response is not None:
        # Convert to standard response format
        if response.status_code >= 400:
            errors = []
            
            if isinstance(response.data, dict):
                if 'detail' in response.data:
                    errors.append({'field': 'general', 'messages': [response.data['detail']]})
                else:
                    for field, messages in response.data.items():
                        if isinstance(messages, list):
                            errors.append({'field': field, 'messages': messages})
                        else:
                            errors.append({'field': field, 'messages': [str(messages)]})
            elif isinstance(response.data, list):
                errors.append({'field': 'general', 'messages': response.data})
            else:
                errors.append({'field': 'general', 'messages': [str(response.data)]})
            
            return StandardResponse.error(
                message=response.data.get('detail', 'An error occurred') if isinstance(response.data, dict) else str(response.data),
                errors=errors,
                status_code=response.status_code
            )
    
    # Handle custom API errors
    if isinstance(exc, APIError):
        return exc.get_response()
    
    # Handle unhandled exceptions
    return StandardResponse.server_error(
        message='An unexpected error occurred',
        metadata={'exception_type': type(exc).__name__}
    )
