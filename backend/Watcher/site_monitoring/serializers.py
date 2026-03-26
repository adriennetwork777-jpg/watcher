from rest_framework import serializers
from django.conf import settings
from django.utils import timezone
import requests
from rest_framework.exceptions import NotFound, AuthenticationFailed

from Watcher.dns_finder.models import DnsTwisted
from .core import monitoring_init
from .models import Alert, Site, TakedownStatus, Company, TakedownRequest

from pymisp import PyMISP, MISPEvent
from Watcher.common.misp import create_misp_tags, create_or_update_objects, get_misp_uuid, update_misp_uuid
from Watcher.common.models import LegitimateDomain

import urllib3
import tldextract
import threading

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class CompanySerializer(serializers.ModelSerializer):
    """
    Serializer for Company model.
    Provides company information with related object counts.
    """
    sites_count = serializers.SerializerMethodField()
    legitimate_domains_count = serializers.SerializerMethodField()
    takedown_requests_count = serializers.SerializerMethodField()
    
    def get_sites_count(self, obj):
        """Get count of sites monitored for this company"""
        return obj.sites.count()
    
    def get_legitimate_domains_count(self, obj):
        """Get count of legitimate domains for this company"""
        return obj.legitimate_domains.count()
    
    def get_takedown_requests_count(self, obj):
        """Get count of takedown requests for this company"""
        return obj.takedown_requests.count()
    
    class Meta:
        model = Company
        fields = ['id', 'name', 'description', 'is_active', 'takedown_credits', 
                  'last_credit_purchase', 'created_at', 'updated_at', 
                  'sites_count', 'legitimate_domains_count', 'takedown_requests_count']
        read_only_fields = ['created_at', 'updated_at', 'last_credit_purchase']


class TakedownRequestSerializer(serializers.ModelSerializer):
    """
    Serializer for TakedownRequest model.
    Handles creation and display of takedown requests.
    """
    site_domain = serializers.CharField(source='site.domain_name', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    submitted_by_username = serializers.CharField(source='submitted_by.username', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = TakedownRequest
        fields = '__all__'
        read_only_fields = ['submitted_at', 'updated_at', 'completed_at', 'submitted_by']


class TakedownCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a takedown request.
    Validates that the company has sufficient credits.
    """
    site_id = serializers.IntegerField()
    notes = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    
    def validate_site_id(self, value):
        """Validate that the site exists"""
        try:
            site = Site.objects.get(pk=value)
            return value
        except Site.DoesNotExist:
            raise serializers.ValidationError(f"Site with ID {value} does not exist")
    
    def save(self, **kwargs):
        """
        Create a takedown request after validating credits.
        Returns the created TakedownRequest instance.
        """
        site_id = self.validated_data['site_id']
        notes = self.validated_data.get('notes', '')
        user = kwargs.get('user')
        
        if not user:
            raise serializers.ValidationError("User is required")
        
        # Get the site
        site = Site.objects.get(pk=site_id)
        
        # Get or create company association
        company = site.company
        if not company:
            raise serializers.ValidationError("This site is not associated with any company")
        
        # Check if company has credits
        if not company.has_takedown_credits():
            raise serializers.ValidationError(
                "Insufficient takedown credits. Please purchase more credits."
            )
        
        # Consume one credit
        company.consume_takedown_credit()
        
        # Create the takedown request
        takedown_request = TakedownRequest.objects.create(
            site=site,
            company=company,
            submitted_by=user,
            status=TakedownStatus.SUBMITTED,
            notes=notes
        )
        
        # Update site's takedown status
        site.takedown_status = TakedownStatus.SUBMITTED
        site.takedown_submitted_at = timezone.now()
        site.save(update_fields=['takedown_status', 'takedown_submitted_at'])
        
        return takedown_request


# Site Serializer
class SiteSerializer(serializers.ModelSerializer):
    """
    Serializer for Site model.
    Includes company information and takedown details.
    """
    misp_event_uuid = serializers.SerializerMethodField()
    company_name = serializers.CharField(source='company.name', read_only=True)
    takedown_status_label = serializers.CharField(source='get_takedown_status_display', read_only=True)
    
    # Backward compatibility for old takedown_request field
    takedown_request = serializers.SerializerMethodField()
    
    def get_takedown_request(self, obj):
        """Backward compatibility - returns True if takedown has been submitted"""
        return obj.is_takedown_submitted

    def get_misp_event_uuid(self, obj):
        """Get MISP UUIDs associated with this domain"""
        return get_misp_uuid(obj.domain_name)

    def validate_domain_name(self, value):
        """Validate domain name format and check for conflicts"""
        extracted = tldextract.extract(value)

        if not extracted.domain or not extracted.suffix:
            raise serializers.ValidationError("The domain name is not valid")

        if self.instance is None:
            if LegitimateDomain.objects.filter(domain_name=value).exists():
                raise serializers.ValidationError(
                    f'{value} Already exists in Legitimate Domains'
                )
        else:
            current = getattr(self.instance, 'domain_name', None)
            if value != current and LegitimateDomain.objects.filter(domain_name=value).exists():
                raise serializers.ValidationError(
                    f'{value} Already exists in Legitimate Domains'
                )

        return value

    def to_internal_value(self, data):
        """Convert empty strings to None for date fields"""
        # Convert "" to None for date fields
        if data.get("expiry") == "":
            data["expiry"] = None
        if data.get("domain_expiry") == "":
            data["domain_expiry"] = None
        if data.get("domain_created_at") == "":
            data["domain_created_at"] = None
        if data.get("ssl_expiry") == "":
            data["ssl_expiry"] = None
        return super().to_internal_value(data)

    def create(self, validated_data):
        """Create site and start monitoring in background thread"""
        site = super().create(validated_data)
        thread = threading.Thread(target=monitoring_init, args=(site,))
        thread.start()
        return site

    class Meta:
        model = Site
        fields = '__all__'


# Alert Serializer
class AlertSerializer(serializers.ModelSerializer):
    """Serializer for Alert model with nested Site information"""
    site = SiteSerializer()

    class Meta:
        model = Alert
        fields = '__all__'


# MISP Serializer
class MISPSerializer(serializers.Serializer):
    """Serializer for MISP event creation/update operations"""
    id = serializers.IntegerField()
    event_uuid = serializers.CharField(required=False, allow_blank=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.misp_api = PyMISP(
            settings.MISP_URL,
            settings.MISP_KEY,
            settings.MISP_VERIFY_SSL,
        )
        self._message = ""

    def validate(self, data):
        """
        Validate the input data.
        """
        try:
            site_id = data['id']
            event_uuid = data.get('event_uuid', '')

            try:
                site = Site.objects.get(pk=site_id)
            except Site.DoesNotExist:
                raise serializers.ValidationError({"id": "Site not found"})

            if event_uuid:
                try:
                    event = self.misp_api.get_event(event_uuid)
                    if not event:
                        raise serializers.ValidationError(
                            {"event_uuid": "MISP event not found"}
                        )
                except Exception as e:
                    raise serializers.ValidationError(
                        {"event_uuid": f"Invalid MISP event UUID: {str(e)}"}
                    )

            return data

        except Exception as e:
            raise serializers.ValidationError(f"Validation error: {str(e)}")

    def save(self):
        """
        Create or update MISP event.
        """
        try:
            site_id = self.validated_data['id']
            event_uuid = self.validated_data.get('event_uuid')
            site = Site.objects.get(pk=site_id)

            if event_uuid:
                event = self.misp_api.get_event(event_uuid)
                success, message = create_or_update_objects(
                    self.misp_api,
                    event,
                    site
                )

                if success:
                    update_misp_uuid(site.domain_name, event_uuid)

            else:
                event = MISPEvent()
                event.distribution = 0
                event.threat_level_id = 2
                event.analysis = 0
                event.info = f"Suspicious domain name {site.domain_name}"
                event.tags = create_misp_tags(self.misp_api)

                event = self.misp_api.add_event(event, pythonify=True)
                success, message = create_or_update_objects(
                    self.misp_api,
                    {'Event': {'id': event.id, 'uuid': event.uuid}},
                    site
                )

                if success:
                    update_misp_uuid(site.domain_name, event.uuid)

            if not success:
                raise serializers.ValidationError(message)

            self._message = message
            return {
                "message": message,
                "misp_event_uuid": get_misp_uuid(site.domain_name),
                "status": "success"
            }

        except Exception as e:
            raise serializers.ValidationError(f"Error with MISP: {str(e)}")

    @property
    def data(self):
        site_id = self.validated_data['id']
        site = Site.objects.get(pk=site_id)
        return {
            'id': site_id,
            'misp_event_uuid': get_misp_uuid(site.domain_name),
            'message': self._message
        }
