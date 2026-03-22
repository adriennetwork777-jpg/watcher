# coding=utf-8
from django.db import models
from django.utils import timezone
from django_mysql.models import ListCharField
from django.contrib.auth.models import User
from django.db.models.signals import pre_save, post_delete
from django.dispatch import receiver


class Company(models.Model):
    """
    Stores company information. All monitored objects are linked to a company.
    """
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Company'
        verbose_name_plural = 'Companies'
    
    def __str__(self):
        return self.name


class TakedownStatus(models.TextChoices):
    NOT_SUBMITTED = 'not_submitted', 'Not Submitted'
    SUBMITTED = 'submitted', 'Submitted'
    WAITING = 'waiting', 'Waiting'
    REFUSED = 'refused', 'Refused'
    TAKEN_DOWN = 'taken_down', 'Taken Down'


class Site(models.Model):
    """
    Stores a site which will be monitor (discrepancy in the hosting or in its DNS resolution, content hosted).
    """
    domain_name = models.CharField(max_length=100, unique=True)
    company = models.ForeignKey(
        Company, 
        on_delete=models.CASCADE, 
        related_name='sites',
        null=True,
        blank=True
    )
    ticket_id = models.CharField(max_length=20, blank=True, null=True)
    rtir = models.IntegerField(unique=True, blank=True, null=True)
    ip = models.GenericIPAddressField(blank=True, null=True)
    ip_second = models.GenericIPAddressField(blank=True, null=True)
    ip_monitoring = models.BooleanField(default=True)
    mail_A_record_ip = models.GenericIPAddressField(blank=True, null=True)
    MX_records = ListCharField(
        base_field=models.CharField(max_length=100),
        size=10,
        max_length=(10 * 101),  # 6 * 100 character nominals, plus commas
        blank=True,
        null=True
    )
    mail_monitoring = models.BooleanField(default=True)
    content_fuzzy_hash = models.CharField(max_length=100, blank=True, null=True)
    content_monitoring = models.BooleanField(default=True)
    monitored = models.BooleanField(default=False, blank=True, null=True)
    web_status = models.IntegerField(blank=True, null=True)

    registrar = models.CharField(max_length=255, blank=True, null=True)
    legitimacy = models.IntegerField(choices=[
        (1, "Unknown"),
        (2, "Suspicious, not harmful"),
        (3, "Suspicious, likely harmful (registered)"),
        (4, "Suspicious, likely harmful (available/disabled)"),
        (5, "Malicious (registered)"),
        (6, "Malicious (available/disabled)"),
    ], blank=True, null=True)
    
    # Updated takedown fields
    takedown_status = models.CharField(
        max_length=20,
        choices=TakedownStatus.choices,
        default=TakedownStatus.NOT_SUBMITTED
    )
    takedown_submitted_at = models.DateTimeField(blank=True, null=True)
    takedown_completed_at = models.DateTimeField(blank=True, null=True)
    takedown_notes = models.TextField(blank=True, null=True)
    
    legal_team = models.BooleanField(default=False)
    blocking_request = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)
    expiry = models.DateTimeField(blank=True, null=True)  # End of monitoring
    domain_expiry = models.DateField(blank=True, null=True)  # Domain expiration date
    domain_created_at = models.DateField(blank=True, null=True)  # Domain registration date
    ssl_expiry = models.DateField(blank=True, null=True)  # SSL certificate expiration date

    def auto_update_legitimacy_on_registration(self):
        """
        Auto-update legitimacy when domain becomes registered (registrar found)
        """
        if self.registrar:
            old_legitimacy = self.legitimacy
            if self.legitimacy == 6:
                self.legitimacy = 5
                return True
            elif self.legitimacy == 4:
                self.legitimacy = 3
                return True
        return False

    class Meta:
        ordering = ["-rtir"]
        verbose_name = 'Website'
        verbose_name_plural = 'Suspicious Websites Monitored'

    def __str__(self):
        return self.domain_name
    
    @property
    def is_takedown_submitted(self):
        """Check if takedown request has been submitted"""
        return self.takedown_status in [
            TakedownStatus.SUBMITTED,
            TakedownStatus.WAITING,
            TakedownStatus.REFUSED,
            TakedownStatus.TAKEN_DOWN
        ]
    
    @property
    def is_takedown_completed(self):
        """Check if takedown has been completed"""
        return self.takedown_status == TakedownStatus.TAKEN_DOWN


@receiver(pre_save, sender=Site)
def set_rtir(sender, instance, **kwargs):
    if instance.rtir is None:
        last_site = Site.objects.order_by('-rtir').first()
        instance.rtir = 1 if not last_site else last_site.rtir + 1


@receiver(pre_save, sender=Site)
def update_takedown_timestamps(sender, instance, **kwargs):
    """
    Automatically update takedown timestamps based on status changes
    """
    if instance.pk:  # Only on update
        try:
            old_instance = Site.objects.get(pk=instance.pk)
            
            # Update submitted_at when status changes to SUBMITTED or WAITING
            if old_instance.takedown_status != instance.takedown_status:
                if instance.takedown_status in [TakedownStatus.SUBMITTED, TakedownStatus.WAITING]:
                    if not instance.takedown_submitted_at:
                        instance.takedown_submitted_at = timezone.now()
                
                # Update completed_at when status changes to TAKEN_DOWN
                elif instance.takedown_status == TakedownStatus.TAKEN_DOWN:
                    if not instance.takedown_completed_at:
                        instance.takedown_completed_at = timezone.now()
        except Site.DoesNotExist:
            pass


class Alert(models.Model):
    """
    Triggered when there is a site status change.
    """
    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    type = models.CharField(max_length=100, default="")
    difference_score = models.IntegerField(blank=True, null=True)
    new_ip = models.GenericIPAddressField(blank=True, null=True)
    new_ip_second = models.GenericIPAddressField(blank=True, null=True)
    new_MX_records = ListCharField(
        base_field=models.CharField(max_length=100),
        size=10,
        max_length=(10 * 101),  # 6 * 100 character nominals, plus commas
        blank=True,
        null=True
    )
    new_mail_A_record_ip = models.GenericIPAddressField(blank=True, null=True)
    old_ip = models.GenericIPAddressField(blank=True, null=True)
    old_ip_second = models.GenericIPAddressField(blank=True, null=True)
    old_MX_records = ListCharField(
        base_field=models.CharField(max_length=100),
        size=10,
        max_length=(10 * 101),  # 6 * 100 character nominals, plus commas
        blank=True,
        null=True
    )
    old_mail_A_record_ip = models.GenericIPAddressField(blank=True, null=True)

    new_registrar = models.CharField(max_length=255, blank=True, null=True)
    old_registrar = models.CharField(max_length=255, blank=True, null=True)
    new_expiry_date = models.DateField(blank=True, null=True)
    old_expiry_date = models.DateField(blank=True, null=True)
    new_ssl_expiry = models.DateField(blank=True, null=True)
    old_ssl_expiry = models.DateField(blank=True, null=True)

    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.site.domain_name} - {self.type}"

    @property
    def is_rdap_alert(self):
        """Check if this is an RDAP/WHOIS alert"""
        return (self.new_registrar is not None or self.old_registrar is not None or
                self.new_expiry_date is not None or self.old_expiry_date is not None)

    @property
    def is_ssl_alert(self):
        """Check if this is an SSL certificate alert"""
        return (self.new_ssl_expiry is not None or self.old_ssl_expiry is not None)


class Subscriber(models.Model):
    """
    List of the alert subscriber(s).
    """
    user_rec = models.ForeignKey(User, on_delete=models.CASCADE, related_name='site_monitoring')
    created_at = models.DateTimeField(default=timezone.now)

    email = models.BooleanField(default=False, verbose_name="E-mail")
    thehive = models.BooleanField(default=False, verbose_name="TheHive")
    slack = models.BooleanField(default=False, verbose_name="Slack")
    citadel = models.BooleanField(default=False, verbose_name="Citadel")

    class Meta:
        verbose_name_plural = 'subscribers'

    def __str__(self):
        return f'{self.user_rec.username} - {self.created_at}'


@receiver(post_delete, sender=Site)
def handle_site_deletion(sender, instance, **kwargs):
    """
    Signal triggered after deleting a site.
    Checks if the domain is still monitored elsewhere, otherwise removes the MISP mapping.
    """
    from common.models import MISPEventUuidLink
    MISPEventUuidLink.check_and_delete_unused_domain(instance.domain_name)
