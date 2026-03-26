from django.contrib import admin
from django.utils.html import format_html
from .models import Alert, Site, Subscriber, Company, TakedownRequest, TakedownStatus
from import_export import resources
from import_export.admin import ExportMixin
from Watcher.common.misp import get_misp_uuid


def custom_titled_filter(title):
    """
    Custom wrapper to add a title to admin filters.
    """
    class Wrapper(admin.FieldListFilter):
        def __new__(cls, *args, **kwargs):
            instance = admin.FieldListFilter.create(*args, **kwargs)
            instance.title = title
            return instance

    return Wrapper


class AlertResource(resources.ModelResource):
    """
    Export resource for Alert model.
    Allows exporting alerts to CSV, Excel, etc.
    """
    class Meta:
        model = Alert


@admin.register(Alert)
class AlertAdmin(ExportMixin, admin.ModelAdmin):
    """
    Admin configuration for Alert model.
    Displays alert details and allows enabling/disabling alerts.
    """
    list_display = ['id', 'type', 'site', 'new_ip', 'new_ip_second', 'new_MX_records', 'new_mail_A_record_ip', 'old_ip',
                    'old_ip_second', 'old_MX_records', 'old_mail_A_record_ip', 'difference_score',
                    'status', 'created_at']
    list_filter = ('site', ('status', custom_titled_filter('Active Status')))
    search_fields = ['id', 'new_ip', 'new_ip_second', 'old_ip', 'old_ip_second', 'difference_score', 'new_MX_records',
                     'new_mail_A_record_ip', 'old_MX_records', 'old_mail_A_record_ip']
    resource_class = AlertResource

    def has_add_permission(self, request):
        """Prevent manual creation of alerts (they are auto-generated)"""
        return False

    def make_disable(self, request, queryset):
        """Action to disable selected alerts"""
        rows_updated = queryset.update(status=False)

        if rows_updated == 1:
            message_bit = "1 alert was"
        else:
            message_bit = "%s alerts were" % rows_updated
        self.message_user(request, "%s successfully marked as disable." % message_bit)

    make_disable.short_description = "Disable selected alerts"

    def make_enable(self, request, queryset):
        """Action to enable selected alerts"""
        rows_updated = queryset.update(status=True)

        if rows_updated == 1:
            message_bit = "1 alert was"
        else:
            message_bit = "%s alerts were" % rows_updated
        self.message_user(request, "%s successfully marked as enable." % message_bit)

    make_enable.short_description = "Enable selected alerts"

    actions = [make_disable, make_enable]


class SiteResource(resources.ModelResource):
    """
    Export resource for Site model.
    Excludes internal monitoring fields.
    """
    class Meta:
        model = Site
        exclude = (
            'misp_event_uuid', 'monitored', 'content_monitoring', 'content_fuzzy_hash', 'mail_monitoring',
            'ip_monitoring')


class TakedownRequestInline(admin.TabularInline):
    """
    Inline display of takedown requests within Site admin.
    Shows all takedown requests for a given site.
    """
    model = TakedownRequest
    extra = 0
    readonly_fields = ['submitted_by', 'submitted_at', 'completed_at', 'external_reference']
    fields = ['status', 'company', 'submitted_by', 'submitted_at', 'completed_at', 'notes', 'external_reference']
    
    def has_add_permission(self, request, obj=None):
        """Prevent manual creation from inline (use API instead)"""
        return False


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    """
    Admin configuration for Company model.
    Manages company information and takedown credits.
    """
    list_display = ['name', 'is_active', 'takedown_credits', 'last_credit_purchase', 'created_at', 'updated_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Company Information', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Takedown Credits', {
            'fields': ('takedown_credits', 'last_credit_purchase'),
            'description': 'Manage takedown credits for this company. Each takedown request consumes 1 credit.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['add_10_credits', 'add_20_credits', 'add_50_credits']
    
    def add_10_credits(self, request, queryset):
        """Add 10 takedown credits to selected companies"""
        for company in queryset:
            company.add_takedown_credits(10)
        self.message_user(request, f"Successfully added 10 credits to {queryset.count()} companies.")
    
    add_10_credits.short_description = "Add 10 takedown credits"
    
    def add_20_credits(self, request, queryset):
        """Add 20 takedown credits to selected companies"""
        for company in queryset:
            company.add_takedown_credits(20)
        self.message_user(request, f"Successfully added 20 credits to {queryset.count()} companies.")
    
    add_20_credits.short_description = "Add 20 takedown credits"
    
    def add_50_credits(self, request, queryset):
        """Add 50 takedown credits to selected companies"""
        for company in queryset:
            company.add_takedown_credits(50)
        self.message_user(request, f"Successfully added 50 credits to {queryset.count()} companies.")
    
    add_50_credits.short_description = "Add 50 takedown credits"


@admin.register(TakedownRequest)
class TakedownRequestAdmin(admin.ModelAdmin):
    """
    Admin configuration for TakedownRequest model.
    Manages takedown requests and their lifecycle.
    """
    list_display = ['id', 'site', 'company', 'status_badge', 'submitted_by', 'submitted_at', 'completed_at']
    list_filter = ['status', 'company', 'submitted_at', 'completed_at']
    search_fields = ['site__domain_name', 'company__name', 'external_reference', 'notes']
    readonly_fields = ['submitted_at', 'updated_at', 'completed_at']
    
    fieldsets = (
        ('Request Details', {
            'fields': ('site', 'company', 'status', 'submitted_by')
        }),
        ('Timeline', {
            'fields': ('submitted_at', 'updated_at', 'completed_at'),
            'description': 'Automatic timestamps tracking the request lifecycle.'
        }),
        ('Additional Information', {
            'fields': ('notes', 'external_reference'),
            'description': 'Internal notes and external reference IDs.'
        }),
    )
    
    actions = ['mark_as_submitted', 'mark_as_waiting', 'mark_as_refused', 'mark_as_taken_down']
    
    def status_badge(self, obj):
        """Display status with color coding"""
        colors = {
            TakedownStatus.NOT_SUBMITTED: '#9e9e9e',
            TakedownStatus.SUBMITTED: '#2196F3',
            TakedownStatus.WAITING: '#FF9800',
            TakedownStatus.REFUSED: '#f44336',
            TakedownStatus.TAKEN_DOWN: '#4CAF50',
        }
        color = colors.get(obj.status, '#9e9e9e')
        return format_html(
            '<span style="color: white; background-color: {}; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def mark_as_submitted(self, request, queryset):
        """Mark selected requests as submitted"""
        updated = queryset.update(status=TakedownStatus.SUBMITTED)
        self.message_user(request, f"{updated} requests marked as submitted.")
    
    mark_as_submitted.short_description = "Mark as Submitted"
    
    def mark_as_waiting(self, request, queryset):
        """Mark selected requests as waiting"""
        updated = queryset.update(status=TakedownStatus.WAITING)
        self.message_user(request, f"{updated} requests marked as waiting.")
    
    mark_as_waiting.short_description = "Mark as Waiting"
    
    def mark_as_refused(self, request, queryset):
        """Mark selected requests as refused"""
        for request_obj in queryset:
            request_obj.mark_as_refused()
        self.message_user(request, f"{queryset.count()} requests marked as refused.")
    
    mark_as_refused.short_description = "Mark as Refused"
    
    def mark_as_taken_down(self, request, queryset):
        """Mark selected requests as taken down (completed)"""
        for request_obj in queryset:
            request_obj.mark_as_completed()
        self.message_user(request, f"{queryset.count()} requests marked as taken down.")
    
    mark_as_taken_down.short_description = "Mark as Taken Down"


@admin.register(Site)
class SiteAdmin(ExportMixin, admin.ModelAdmin):
    """
    Admin configuration for Site model.
    Displays monitored sites with takedown information.
    """
    list_display = ['rtir', 'domain_name', 'company', 'ticket_id', 'registrar', 'legitimacy', 
                    'takedown_status_badge', 'takedown_submitted_at', 'takedown_completed_at',
                    'ip', 'ip_second', 'monitored', 'web_status', 'legal_team', 'blocking_request',
                    'display_misp_uuid', 'created_at', 'expiry', 'domain_created_at', 'domain_expiry', 'ssl_expiry']
    list_filter = [
        'company',
        'created_at',
        'expiry',
        'domain_created_at',
        'domain_expiry',
        'ssl_expiry',
        'monitored',
        'web_status',
        'legitimacy',
        'takedown_status',
        'legal_team',
        'blocking_request']
    search_fields = ['rtir', 'domain_name', 'ip', 'ip_second', 'registrar']
    resource_class = SiteResource
    readonly_fields = ['display_misp_uuid']
    inlines = [TakedownRequestInline]
    
    def has_add_permission(self, request):
        """Prevent manual creation of sites (use API instead)"""
        return False
    
    def takedown_status_badge(self, obj):
        """Display takedown status with color coding"""
        colors = {
            TakedownStatus.NOT_SUBMITTED: '#9e9e9e',
            TakedownStatus.SUBMITTED: '#2196F3',
            TakedownStatus.WAITING: '#FF9800',
            TakedownStatus.REFUSED: '#f44336',
            TakedownStatus.TAKEN_DOWN: '#4CAF50',
        }
        color = colors.get(obj.takedown_status, '#9e9e9e')
        return format_html(
            '<span style="color: white; background-color: {}; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_takedown_status_display()
        )
    takedown_status_badge.short_description = 'Takedown Status'

    def display_misp_uuid(self, obj):
        """Display MISP UUIDs associated with the domain"""
        uuid = get_misp_uuid(obj.domain_name)
        if not uuid:
            return "-"

        if len(uuid) == 1:
            return uuid[0]
        else:
            return ", ".join(uuid)

    display_misp_uuid.short_description = "MISP Event UUID"


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    """
    Admin configuration for Subscriber model.
    Manages alert notification preferences.
    """
    list_display = ('user_rec', 'created_at', 'email', 'thehive', 'slack', 'citadel')
    list_filter = ('email', 'thehive', 'slack', 'citadel')
    search_fields = ('user_rec__username',)
    fieldsets = (
        (None, {
            'fields': ('user_rec', 'created_at')
        }),
        ('Notification Channels', {
            'fields': ('email', 'thehive', 'slack', 'citadel'),
            'description': "Select the notification channels for this subscriber."
        }),
    )
