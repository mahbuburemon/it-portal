from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class TeamMember(models.Model):
    """The 14 IT Team members who attend and submit checklists without login."""
    name = models.CharField(max_length=150)
    employee_id = models.CharField(max_length=50, unique=True)
    designation = models.CharField(max_length=150)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'IT Team Member'
        verbose_name_plural = 'IT Team Members'

    def __str__(self):
        return f"{self.name} ({self.designation})"


class ChecklistTemplate(models.Model):
    """Definition for each of the 12 BIFPCL Word Checklists."""
    doc_no = models.CharField(max_length=50, unique=True, help_text="e.g. BIFPCL/IT/F/01")
    title = models.CharField(max_length=255, help_text="e.g. CCTV Troubleshooting Report & Checklist")
    category = models.CharField(max_length=100, help_text="e.g. Surveillance, Network, Systems, Power")
    revision = models.CharField(max_length=20, default="Rev: 00")
    effective_date = models.DateField(default=timezone.now)
    retention_period = models.CharField(max_length=50, default="3 Years")
    icon = models.CharField(max_length=50, default="camera-video", help_text="Bootstrap icon name")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    # Dynamic schemas
    equipment_fields_schema = models.JSONField(
        default=list,
        help_text="List of equipment fields: [{'key': 'camera_id', 'label': 'Camera ID / Name', 'placeholder': '...'}, {'key': 'location', 'label': 'Location'}]"
    )
    diagnostic_items_schema = models.JSONField(
        default=list,
        help_text="List of inspection checklist items: [{'id': 1, 'text': 'Correct camera ID and location confirmed'}]"
    )
    fault_options_schema = models.JSONField(
        default=list,
        help_text="List of fault classifications: [{'key': 'minor', 'label': '1. Minor issue corrected', 'desc': 'Loose power plug...'}]"
    )
    materials_enabled = models.BooleanField(default=True)
    verification_items_schema = models.JSONField(
        default=list,
        help_text="List of verification items: ['Camera online and live view stable', 'Field of view acceptable']"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['doc_no']
        verbose_name = 'Checklist Template'
        verbose_name_plural = 'Checklist Templates'

    def __str__(self):
        return f"{self.doc_no} - {self.title}"


class ChecklistSubmission(models.Model):
    """
    Unified submission record representing the 3-stage lifecycle:
    Stage 1: Attended by (IT Team Member, no login)
    Stage 2: Supervised by (Supervisor, login, review & forward)
    Stage 3: Approved by (Assistant Manager / Deputy Manager, login, final approval)
    """
    STATUS_CHOICES = [
        ('SUBMITTED', 'Submitted (Pending Supervisor Review)'),
        ('FORWARDED', 'Forwarded (Pending Final Approval)'),
        ('APPROVED', 'Approved (Finalized)'),
        ('RETURNED', 'Returned for Revision'),
    ]

    tracking_no = models.CharField(max_length=50, unique=True, editable=False)
    template = models.ForeignKey(ChecklistTemplate, on_delete=models.CASCADE, related_name='submissions')

    # Header / Outage Information
    work_request_no = models.CharField(max_length=100, blank=True)
    report_date = models.DateField(default=timezone.now)
    reported_by = models.CharField(max_length=150, blank=True)
    contact_no = models.CharField(max_length=100, blank=True)
    
    outage_reported_at = models.DateTimeField(null=True, blank=True)
    site_arrival_at = models.DateTimeField(null=True, blank=True)
    restored_at = models.DateTimeField(null=True, blank=True)
    total_downtime = models.CharField(max_length=100, blank=True)

    # Dynamic Section Data
    equipment_data = models.JSONField(default=dict, blank=True)
    diagnostics_data = models.JSONField(default=dict, blank=True)
    fault_selected = models.CharField(max_length=100, blank=True)
    action_taken_details = models.TextField(blank=True)
    materials_data = models.JSONField(default=list, blank=True)
    
    faulty_item_disposal = models.CharField(max_length=100, blank=True)
    disposal_ref_no = models.CharField(max_length=100, blank=True)
    warranty_status = models.CharField(max_length=100, blank=True)
    vendor_po_ref = models.CharField(max_length=100, blank=True)

    verification_checks = models.JSONField(default=list, blank=True)
    final_status = models.CharField(max_length=100, default='Restored and Closed')
    final_status_other = models.CharField(max_length=150, blank=True)
    additional_findings = models.TextField(blank=True)

    # Status tracking
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='SUBMITTED')

    # STAGE 1: Attended by (Multiple IT Team Members can attend)
    attended_by = models.ManyToManyField(TeamMember, related_name='submissions')
    submitted_at = models.DateTimeField(auto_now_add=True)
    client_ip = models.GenericIPAddressField(null=True, blank=True)

    # STAGE 2: Supervised by (1 of 3 Supervisors)
    supervised_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='supervised_checklists'
    )
    supervised_at = models.DateTimeField(null=True, blank=True)
    supervisor_remarks = models.TextField(blank=True)

    # STAGE 3: Approved by (1 Assistant Manager or 1 Deputy Manager)
    approved_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='approved_checklists'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    manager_remarks = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Checklist Submission'
        verbose_name_plural = 'Checklist Submissions'

    @property
    def attended_by_display(self):
        names = [m.name for m in self.attended_by.all()]
        return ", ".join(names) if names else "None"

    @property
    def supervised_by_display(self):
        if self.supervised_by:
            return self.supervised_by.get_full_name() or self.supervised_by.username
        return ""

    @property
    def approved_by_display(self):
        if self.approved_by:
            return self.approved_by.get_full_name() or self.approved_by.username
        return ""

    def save(self, *args, **kwargs):
        if not self.tracking_no:
            date_str = timezone.now().strftime('%Y%m%d')
            rand_suffix = uuid.uuid4().hex[:4].upper()
            self.tracking_no = f"BIFPCL-{date_str}-{rand_suffix}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tracking_no} - {self.template.doc_no} ({self.get_status_display()})"
