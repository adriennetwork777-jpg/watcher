# -*- coding: utf-8 -*-
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from Watcher.site_monitoring.models import Company


class TakedownCredit(models.Model):
    """
    Stores takedown credits for each company.
    Each company has a credit pack that can be used to submit takedown requests.
    """
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name='takedown_credit',
        null=True,
        blank=True
    )
    credits_remaining = models.PositiveIntegerField(default=0)
    total_credits_purchased = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Takedown Credit'
        verbose_name_plural = 'Takedown Credits'
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.company.name if self.company else 'No Company'} - {self.credits_remaining} credits"
    
    def has_credits(self, amount=1):
        """Check if there are enough credits available"""
        return self.credits_remaining >= amount
    
    def consume_credits(self, amount=1):
        """
        Consume credits from the pool.
        Returns True if successful, False if not enough credits.
        """
        if self.has_credits(amount):
            self.credits_remaining -= amount
            self.save()
            return True
        return False
    
    def add_credits(self, amount):
        """Add credits to the pool"""
        self.credits_remaining += amount
        self.total_credits_purchased += amount
        self.save()


class TakedownRequest(models.Model):
    """
    Tracks individual takedown requests with full history.
    Each request consumes one credit from the company's pool.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('in_progress', 'In Progress'),
        ('acknowledged', 'Acknowledged by Provider'),
        ('refused', 'Refused'),
        ('completed', 'Completed - Taken Down'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    # Links
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='takedown_requests'
    )
    site = models.ForeignKey(
        'site_monitoring.Site',
        on_delete=models.CASCADE,
        related_name='takedown_requests',
        null=True,
        blank=True
    )
    requested_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='requested_takedowns'
    )
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_takedowns'
    )
    
    # Request details
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='normal'
    )
    reason = models.TextField(
        help_text="Reason for takedown request"
    )
    additional_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes or context"
    )
    
    # Provider information
    provider_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Hosting provider or registrar name"
    )
    provider_contact = models.TextField(
        blank=True,
        null=True,
        help_text="Provider contact information"
    )
    provider_ticket_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Provider's ticket/reference number"
    )
    
    # Dates
    submitted_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the request was submitted to provider"
    )
    acknowledged_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the provider acknowledged the request"
    )
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the takedown was completed"
    )
    estimated_completion = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Estimated completion date"
    )
    
    # Tracking
    credit_consumed = models.BooleanField(
        default=False,
        help_text="Whether a credit was consumed for this request"
    )
    credit_id = models.IntegerField(
        blank=True,
        null=True,
        help_text="Reference to the credit transaction"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Takedown Request'
        verbose_name_plural = 'Takedown Requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['company', '-created_at']),
        ]
    
    def __str__(self):
        domain = self.site.domain_name if self.site else 'N/A'
        return f"Takedown #{self.id} - {domain} ({self.status})"
    
    def can_submit(self):
        """Check if this request can be submitted"""
        return self.status == 'draft' and self.company.takedown_credit.has_credits(1)
    
    def submit(self, user):
        """
        Submit the takedown request.
        Consumes one credit from the company's pool.
        """
        if not self.can_submit():
            return False, "Request cannot be submitted"
        
        if not self.company.takedown_credit.consume_credits(1):
            return False, "Not enough credits"
        
        self.status = 'submitted'
        self.submitted_at = timezone.now()
        self.requested_by = user
        self.credit_consumed = True
        self.save()
        
        # Update the related site's takedown status
        if self.site:
            from Watcher.site_monitoring.models import TakedownStatus
            self.site.takedown_status = TakedownStatus.SUBMITTED
            self.site.takedown_submitted_at = timezone.now()
            self.site.save()
        
        return True, "Takedown request submitted successfully"
    
    def update_status(self, new_status, user=None, notes=None):
        """Update the request status with optional notes"""
        old_status = self.status
        self.status = new_status
        
        now = timezone.now()
        
        if new_status == 'acknowledged' and not self.acknowledged_at:
            self.acknowledged_at = now
        elif new_status == 'completed' and not self.completed_at:
            self.completed_at = now
            if self.site:
                from Watcher.site_monitoring.models import TakedownStatus
                self.site.takedown_status = TakedownStatus.TAKEN_DOWN
                self.site.takedown_completed_at = now
                self.site.save()
        elif new_status == 'cancelled':
            # Optionally refund credit if cancelled early
            pass
        
        if notes:
            if self.additional_notes:
                self.additional_notes += f"\n\n[{now}] Status changed from {old_status} to {new_status}: {notes}"
            else:
                self.additional_notes = f"[{now}] Status changed from {old_status} to {new_status}: {notes}"
        
        if user:
            self.processed_by = user
        
        self.save()
        return True


class TakedownHistory(models.Model):
    """
    Audit log for all takedown request changes.
    """
    ACTION_CHOICES = [
        ('created', 'Created'),
        ('submitted', 'Submitted'),
        ('status_changed', 'Status Changed'),
        ('note_added', 'Note Added'),
        ('credit_consumed', 'Credit Consumed'),
        ('credit_refunded', 'Credit Refunded'),
        ('deleted', 'Deleted'),
    ]
    
    takedown_request = models.ForeignKey(
        TakedownRequest,
        on_delete=models.CASCADE,
        related_name='history'
    )
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES
    )
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    old_value = models.TextField(
        blank=True,
        null=True,
        help_text="Previous value (for status changes)"
    )
    new_value = models.TextField(
        blank=True,
        null=True,
        help_text="New value (for status changes)"
    )
    notes = models.TextField(
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Takedown History'
        verbose_name_plural = 'Takedown Histories'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"#{self.takedown_request.id} - {self.action} at {self.created_at}"
