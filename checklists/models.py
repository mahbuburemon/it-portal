from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class TeamMember(models.Model):
    """The 14 IT Team members who have individual login accounts and personal dashboards."""
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='team_profile'
    )
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

    @property
    def has_outage_tracking(self):
        return bool(self.fault_options_schema)

    @property
    def is_installation(self):
        return 'installation' in self.title.lower()

    @property
    def is_replacement(self):
        return 'replacement' in self.title.lower()

    @property
    def is_ofc(self):
        title_l = self.title.lower()
        return 'optical fiber' in title_l or 'ofc' in self.doc_no.lower() or 'ofc' in title_l

    @property
    def has_disposal(self):
        if self.is_ofc:
            return False
        return not self.is_installation

    @property
    def job_id_label(self):
        if self.has_outage_tracking:
            return "Work Request No."
        return "Job ID"

    @property
    def date_label(self):
        if self.is_ofc:
            return "Record Date"
        if self.is_installation:
            return "Installation Date"
        return "Report Date" if self.has_outage_tracking else "Date"

    @property
    def default_job_id(self):
        title_l = self.title.lower()
        if 'cctv' in title_l and self.is_installation:
            return "BIFPCL/IT/CCTV/INS/2026/"
        elif 'cctv' in title_l and self.is_replacement:
            return "BIFPCL/IT/CCTV/REP/2026/"
        elif 'ap' in title_l and self.is_installation:
            return "BIFPCL/IT/AP/INS/2026/"
        elif 'ap' in title_l and self.is_replacement:
            return "BIFPCL/IT/AP/REP/2026/"
        elif 'telephone' in title_l and self.is_installation:
            return "BIFPCL/IT/TEL/INS/2026/"
        elif 'telephone' in title_l and self.is_replacement:
            return "BIFPCL/IT/TEL/REP/2026/"
        elif 'ofc' in title_l or 'optical fiber' in title_l:
            return "BIFPCL/IT/OFC/2026/"
        return ""

    @property
    def physical_heading(self):
        if self.is_installation or self.is_replacement:
            return "Physical Installation Checklist"
        return "Inspection and Diagnostic Checklist"

    @property
    def verification_heading(self):
        if self.is_replacement:
            return "Post Replacement Verification"
        elif self.is_installation:
            return "Post Installation Verification"
        return "Restoration Verification"

    @property
    def outage_reported_label(self):
        title_l = self.title.lower()
        if 'printer' in title_l or 'desktop' in title_l or 'laptop' in title_l:
            return "Fault Reported At"
        return "Outage Reported At"

    @property
    def site_arrival_label(self):
        title_l = self.title.lower()
        if 'printer' in title_l or 'desktop' in title_l or 'laptop' in title_l:
            return "Attended At"
        return "Site Arrival At"

    @property
    def final_status_choices(self):
        title_l = self.title.lower()
        if 'printer' in title_l:
            return ['Restored and Closed', 'Pending Consumable', 'Pending Spare Parts', 'Pending Vendor Support']
        elif 'desktop' in title_l or 'laptop' in title_l:
            return ['Restored and Closed', 'Pending Spare Parts', 'Pending Replacement', 'Warranty Claim']
        elif 'telephone' in title_l:
            if self.is_installation:
                return ['Commissioned & Closed', 'Pending EPABX Configuration', 'Pending Cable Work']
            elif self.is_replacement:
                return ['Restored and Closed', 'Pending EPABX Configuration', 'Pending Replacement']
            else:  # Troubleshooting
                return ['Restored and Closed', 'Pending EPABX Vendor', 'Pending Replacement']
        elif self.is_installation and 'cctv' in title_l:
            return ['Commissioned & Closed', 'Pending VMS Configuration', 'Pending Power Department']
        elif self.is_installation:
            return ['Commissioned & Closed', 'Pending Power Department', 'Pending Replacement']
        return ['Restored and Closed', 'Pending Power Department', 'Pending Replacement']

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
    custom_data = models.JSONField(default=dict, blank=True)
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

    # STAGE 1: Attended by & Submitted by
    attended_by = models.ManyToManyField(TeamMember, related_name='submissions')
    submitted_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='submitted_checklists'
    )
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

    @property
    def formatted_equipment_fields(self):
        """
        Returns list of dicts ordered according to template.equipment_fields_schema:
        {key, label, value, options, is_options}
        """
        results = []
        schema = self.template.equipment_fields_schema or []
        for field in schema:
            key = field.get('key')
            label = field.get('label', key)
            options = field.get('options', [])
            val = ''
            if isinstance(self.equipment_data, dict) and key in self.equipment_data:
                eq_item = self.equipment_data[key]
                if isinstance(eq_item, dict):
                    val = eq_item.get('value', '')
                else:
                    val = str(eq_item)
            results.append({
                'key': key,
                'label': label,
                'value': val,
                'options': options,
                'is_options': bool(options)
            })
        return results

    def save(self, *args, **kwargs):
        if not self.tracking_no:
            date_str = timezone.now().strftime('%Y%m%d')
            rand_suffix = uuid.uuid4().hex[:4].upper()
            self.tracking_no = f"BIFPCL-{date_str}-{rand_suffix}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tracking_no} - {self.template.doc_no} ({self.get_status_display()})"
