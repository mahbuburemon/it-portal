from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q

# pyrefly: ignore [missing-import]
from .models import TeamMember, ChecklistTemplate, ChecklistSubmission

# pyrefly: ignore [missing-import]
from .rbac import supervisor_required, manager_required, is_supervisor, is_manager
import json


# ==========================================
# PUBLIC VIEWS (No Login Required - IT Team)
# ==========================================

def main_dashboard(request):
    """
    Public Main Dashboard.
    14 IT Team members can access all 12 checklists and complete them without logging in.
    """
    templates = ChecklistTemplate.objects.filter(is_active=True).order_by('doc_no')
    categories = ChecklistTemplate.objects.filter(is_active=True).values_list('category', flat=True).distinct()
    
    # Recent public submissions (last 10)
    recent_submissions = ChecklistSubmission.objects.select_related('template').prefetch_related('attended_by').order_by('-created_at')[:10]
    
    # Stats for today
    today = timezone.now().date()
    today_count = ChecklistSubmission.objects.filter(report_date=today).count()
    completed_today = ChecklistSubmission.objects.filter(report_date=today, status='APPROVED').count()

    context = {
        'templates': templates,
        'categories': categories,
        'recent_submissions': recent_submissions,
        'today_count': today_count,
        'completed_today': completed_today,
    }
    return render(request, 'checklists/main_dashboard.html', context)


def checklist_form(request, template_id):
    """
    Interactive online form for any of the 12 BIFPCL Word Checklists.
    Renders dynamic equipment fields, Yes/No/NA diagnostic checklist,
    fault classification, spares, and restoration verification.
    """
    template_obj = get_object_or_404(ChecklistTemplate, id=template_id, is_active=True)
    team_members = TeamMember.objects.filter(is_active=True).order_by('name')

    if request.method == 'POST':
        # 1. Attended By (Multiple IT Team Members can attend)
        attended_by_ids = request.POST.getlist('attended_by')
        if not attended_by_ids:
            messages.error(request, "Please select at least one IT team member who Attended this checklist.")
            return redirect('checklist_form', template_id=template_id)


        # 2. Header & Outage info
        work_request_no = request.POST.get('work_request_no', '').strip()
        report_date_str = request.POST.get('report_date') or timezone.now().strftime('%Y-%m-%d')
        reported_by = request.POST.get('reported_by', '').strip()
        contact_no = request.POST.get('contact_no', '').strip()
        
        outage_reported_at = request.POST.get('outage_reported_at') or None
        site_arrival_at = request.POST.get('site_arrival_at') or None
        restored_at = request.POST.get('restored_at') or None
        total_downtime = request.POST.get('total_downtime', '').strip()

        # 3. Dynamic Equipment Data
        equipment_data = {}
        for field in template_obj.equipment_fields_schema:
            val = request.POST.get(f"eq_{field['key']}", '').strip()
            equipment_data[field['key']] = {
                'label': field.get('label', field['key']),
                'value': val
            }

        # 4. Diagnostic Checklist Items (Yes / No / N/A + Reading/Remarks)
        diagnostics_data = {}
        for item in template_obj.diagnostic_items_schema:
            item_id = str(item['id'])
            status_val = request.POST.get(f"diag_status_{item_id}", 'N/A')
            remarks_val = request.POST.get(f"diag_remarks_{item_id}", '').strip()
            diagnostics_data[item_id] = {
                'text': item['text'],
                'status': status_val,
                'remarks': remarks_val
            }

        # 5. Fault Classification & Action Taken
        fault_selected = request.POST.get('fault_selected', '')
        action_taken_details = request.POST.get('action_taken_details', '').strip()

        # 6. Materials, Warranty and Disposal
        materials_data = []
        mat_descs = request.POST.getlist('mat_desc[]')
        mat_models = request.POST.getlist('mat_model[]')
        mat_qtys = request.POST.getlist('mat_qty[]')
        mat_refs = request.POST.getlist('mat_ref[]')

        for i in range(len(mat_descs)):
            desc = mat_descs[i].strip()
            if desc:
                materials_data.append({
                    'sl': i + 1,
                    'desc': desc,
                    'model': mat_models[i].strip() if i < len(mat_models) else '',
                    'qty': mat_qtys[i].strip() if i < len(mat_qtys) else '1',
                    'ref': mat_refs[i].strip() if i < len(mat_refs) else ''
                })

        faulty_item_disposal = request.POST.get('faulty_item_disposal', '')
        disposal_ref_no = request.POST.get('disposal_ref_no', '').strip()
        warranty_status = request.POST.get('warranty_status', '')
        vendor_po_ref = request.POST.get('vendor_po_ref', '').strip()

        # 7. Restoration Verification & Final Status
        verification_checks = request.POST.getlist('verification_checks')
        final_status = request.POST.get('final_status', 'Restored and Closed')
        final_status_other = request.POST.get('final_status_other', '').strip()
        additional_findings = request.POST.get('additional_findings', '').strip()

        # Client IP capture
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            client_ip = x_forwarded_for.split(',')[0]
        else:
            client_ip = request.META.get('REMOTE_ADDR')

        # Create submission
        submission = ChecklistSubmission.objects.create(
            template=template_obj,
            work_request_no=work_request_no,
            report_date=report_date_str,
            reported_by=reported_by,
            contact_no=contact_no,
            outage_reported_at=outage_reported_at,
            site_arrival_at=site_arrival_at,
            restored_at=restored_at,
            total_downtime=total_downtime,
            equipment_data=equipment_data,
            diagnostics_data=diagnostics_data,
            fault_selected=fault_selected,
            action_taken_details=action_taken_details,
            materials_data=materials_data,
            faulty_item_disposal=faulty_item_disposal,
            disposal_ref_no=disposal_ref_no,
            warranty_status=warranty_status,
            vendor_po_ref=vendor_po_ref,
            verification_checks=verification_checks,
            final_status=final_status,
            final_status_other=final_status_other,
            additional_findings=additional_findings,
            client_ip=client_ip,
            status='SUBMITTED'
        )
        submission.attended_by.set(attended_by_ids)

        messages.success(request, f"Checklist submitted successfully! Tracking Reference: {submission.tracking_no}")
        return redirect('submission_success', tracking_no=submission.tracking_no)

    context = {
        'template': template_obj,
        'team_members': team_members,
        'today': timezone.now().strftime('%Y-%m-%d'),
    }
    return render(request, 'checklists/checklist_form.html', context)


def submission_success(request, tracking_no):
    """Public confirmation view after successful submission."""
    submission = get_object_or_404(ChecklistSubmission.objects.select_related('template').prefetch_related('attended_by'), tracking_no=tracking_no)
    return render(request, 'checklists/submission_success.html', {'submission': submission})


# ==========================================
# AUTHENTICATION & ROLE ROUTING
# ==========================================

@login_required
def role_redirect(request):
    """Redirects the logged-in user to their respective role dashboard."""
    if is_manager(request.user):
        return redirect('manager_dashboard')
    elif is_supervisor(request.user):
        return redirect('supervisor_dashboard')
    else:
        return redirect('main_dashboard')


# ==========================================
# STAGE 2: SUPERVISOR DASHBOARD & REVIEW
# ==========================================

@supervisor_required
def supervisor_dashboard(request):
    """
    Supervisor Dashboard:
    Any of the 3 Supervisors can see all submitted checklists, review entries,
    and Forward them to the Assistant Manager / Deputy Manager queue.
    """
    status_filter = request.GET.get('status', 'SUBMITTED')
    
    submissions = ChecklistSubmission.objects.select_related('template', 'supervised_by').prefetch_related('attended_by').order_by('-created_at')
    
    if status_filter != 'ALL':
        submissions = submissions.filter(status=status_filter)

    # Counters
    pending_count = ChecklistSubmission.objects.filter(status='SUBMITTED').count()
    forwarded_by_me = ChecklistSubmission.objects.filter(supervised_by=request.user).count()
    total_count = ChecklistSubmission.objects.count()

    context = {
        'submissions': submissions,
        'status_filter': status_filter,
        'pending_count': pending_count,
        'forwarded_by_me': forwarded_by_me,
        'total_count': total_count,
    }
    return render(request, 'checklists/supervisor/dashboard.html', context)


@supervisor_required
def supervisor_review(request, submission_id):
    """Supervisor detailed review & forward action."""
    submission = get_object_or_404(ChecklistSubmission.objects.select_related('template').prefetch_related('attended_by'), id=submission_id)


    if request.method == 'POST':
        action = request.POST.get('action')
        remarks = request.POST.get('supervisor_remarks', '').strip()

        if action == 'forward':
            submission.status = 'FORWARDED'
            submission.supervised_by = request.user
            submission.supervised_at = timezone.now()
            submission.supervisor_remarks = remarks
            submission.save()
            messages.success(request, f"Checklist {submission.tracking_no} successfully reviewed and FORWARDED to Manager Approval Queue.")
            return redirect('supervisor_dashboard')

        elif action == 'return':
            submission.status = 'RETURNED'
            submission.supervised_by = request.user
            submission.supervised_at = timezone.now()
            submission.supervisor_remarks = remarks
            submission.save()
            messages.warning(request, f"Checklist {submission.tracking_no} returned for revision with notes.")
            return redirect('supervisor_dashboard')

    context = {
        'submission': submission,
    }
    return render(request, 'checklists/supervisor/review_detail.html', context)


# ==========================================
# STAGE 3: MANAGER DASHBOARD & APPROVAL
# ==========================================

@manager_required
def manager_dashboard(request):
    """
    Manager Dashboard:
    1 Assistant Manager and 1 Deputy Manager have access.
    Either one can provide the Final Approval ('Approved By').
    """
    status_filter = request.GET.get('status', 'FORWARDED')
    
    submissions = ChecklistSubmission.objects.select_related('template', 'supervised_by', 'approved_by').prefetch_related('attended_by').order_by('-created_at')
    
    if status_filter != 'ALL':
        submissions = submissions.filter(status=status_filter)

    pending_approval_count = ChecklistSubmission.objects.filter(status='FORWARDED').count()
    approved_count = ChecklistSubmission.objects.filter(status='APPROVED').count()
    total_count = ChecklistSubmission.objects.count()

    context = {
        'submissions': submissions,
        'status_filter': status_filter,
        'pending_approval_count': pending_approval_count,
        'approved_count': approved_count,
        'total_count': total_count,
    }
    return render(request, 'checklists/manager/dashboard.html', context)


@manager_required
def manager_approve(request, submission_id):
    """Manager review & final approval action."""
    submission = get_object_or_404(ChecklistSubmission.objects.select_related('template', 'supervised_by').prefetch_related('attended_by'), id=submission_id)

    if request.method == 'POST':
        action = request.POST.get('action')
        remarks = request.POST.get('manager_remarks', '').strip()

        if action == 'approve':
            submission.status = 'APPROVED'
            submission.approved_by = request.user
            submission.approved_at = timezone.now()
            submission.manager_remarks = remarks
            submission.save()
            messages.success(request, f"Checklist {submission.tracking_no} granted FINAL APPROVAL by {request.user.get_full_name() or request.user.username}.")
            return redirect('manager_dashboard')

        elif action == 'return':
            submission.status = 'RETURNED'
            submission.approved_by = request.user
            submission.approved_at = timezone.now()
            submission.manager_remarks = remarks
            submission.save()
            messages.warning(request, f"Checklist {submission.tracking_no} returned for review with remarks.")
            return redirect('manager_dashboard')

    context = {
        'submission': submission,
    }
    return render(request, 'checklists/manager/approval_detail.html', context)


# ==========================================
# REPORT VIEW, AUDIT ARCHIVE & PRINTING
# ==========================================

def checklist_detail(request, submission_id):
    """Detailed read-only inspection of a completed or in-progress checklist."""
    submission = get_object_or_404(ChecklistSubmission.objects.select_related('template', 'supervised_by', 'approved_by').prefetch_related('attended_by'), id=submission_id)
    return render(request, 'checklists/checklist_detail.html', {'submission': submission})


def checklist_print(request, submission_id):
    """
    Print / PDF view reproducing the EXACT physical Word document layout.
    Features:
    - Official BIFPCL Header & logo
    - Metadata table
    - Diagnostic Inspection table
    - Fault Classification
    - Spares & Materials table
    - Verification checkmarks
    - Standard 3-tier signature block (Attended By, Supervised By, Approved By)
    - Document footer (Doc No, Rev, Retention, Page 1 of 1)
    """
    submission = get_object_or_404(ChecklistSubmission.objects.select_related('template', 'supervised_by', 'approved_by').prefetch_related('attended_by'), id=submission_id)
    return render(request, 'checklists/checklist_print.html', {'submission': submission})


@login_required
def audit_archive(request):
    """
    Audit log for authorized staff (Supervisors and Managers) to search and filter
    all checklists by date range, template, technician, and approval status.
    """
    submissions = ChecklistSubmission.objects.select_related('template', 'supervised_by', 'approved_by').prefetch_related('attended_by').order_by('-created_at')

    # Filters
    template_id = request.GET.get('template')
    status = request.GET.get('status')
    technician_id = request.GET.get('technician')
    search_q = request.GET.get('q', '').strip()

    if template_id:
        submissions = submissions.filter(template_id=template_id)
    if status:
        submissions = submissions.filter(status=status)
    if technician_id:
        submissions = submissions.filter(attended_by__id=technician_id).distinct()
    if search_q:
        submissions = submissions.filter(
            Q(tracking_no__icontains=search_q) |
            Q(work_request_no__icontains=search_q) |
            Q(reported_by__icontains=search_q) |
            Q(attended_by__name__icontains=search_q)
        ).distinct()

    templates = ChecklistTemplate.objects.filter(is_active=True).order_by('doc_no')
    team_members = TeamMember.objects.filter(is_active=True).order_by('name')

    context = {
        'submissions': submissions,
        'templates': templates,
        'team_members': team_members,
        'selected_template': template_id,
        'selected_status': status,
        'selected_technician': technician_id,
        'search_q': search_q,
    }
    return render(request, 'checklists/archive.html', context)
