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
    
    # Recent public submissions (up to 100 with DataTables pagination)
    recent_submissions = ChecklistSubmission.objects.select_related('template', 'supervised_by', 'approved_by').prefetch_related('attended_by').order_by('-created_at')[:100]
    
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


def _extract_submission_data(request, template_obj):
    attended_by_ids = request.POST.getlist('attended_by')
    work_request_no = request.POST.get('work_request_no', '').strip()
    report_date_str = request.POST.get('report_date') or timezone.now().strftime('%Y-%m-%d')
    reported_by = request.POST.get('reported_by', '').strip()
    contact_no = request.POST.get('contact_no', '').strip()
    
    outage_reported_at = request.POST.get('outage_reported_at') or None
    site_arrival_at = request.POST.get('site_arrival_at') or None
    restored_at = request.POST.get('restored_at') or None
    total_downtime = request.POST.get('total_downtime', '').strip()

    # Dynamic Equipment Data
    equipment_data = {}
    for field in template_obj.equipment_fields_schema:
        val = request.POST.get(f"eq_{field['key']}", '').strip()
        equipment_data[field['key']] = {
            'label': field.get('label', field['key']),
            'value': val
        }

    # Diagnostic Checklist Items
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

    # Fault Classification & Action Taken
    fault_selected = request.POST.get('fault_selected', '')
    action_taken_details = request.POST.get('action_taken_details', '').strip()

    # Materials
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

    # Restoration Verification & Final Status
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

    # Optical Fiber Cable (F/12) Custom Sections Data
    custom_data = {}
    if template_obj.is_ofc:
        # 1. Cable Laying Details
        cl_rows = []
        cl_drums = request.POST.getlist('ofc_cl_drum[]')
        cl_froms = request.POST.getlist('ofc_cl_from[]')
        cl_tos = request.POST.getlist('ofc_cl_to[]')
        cl_paths = request.POST.getlist('ofc_cl_path[]')
        cl_starts = request.POST.getlist('ofc_cl_start[]')
        cl_ends = request.POST.getlist('ofc_cl_end[]')
        cl_laids = request.POST.getlist('ofc_cl_laid[]')
        cl_slacks = request.POST.getlist('ofc_cl_slack[]')
        cl_remarks = request.POST.getlist('ofc_cl_remarks[]')
        for i in range(len(cl_drums)):
            cl_rows.append({
                'sl': i + 1,
                'drum': cl_drums[i].strip() if i < len(cl_drums) else '',
                'from': cl_froms[i].strip() if i < len(cl_froms) else '',
                'to': cl_tos[i].strip() if i < len(cl_tos) else '',
                'path': cl_paths[i].strip() if i < len(cl_paths) else 'Duct',
                'start': cl_starts[i].strip() if i < len(cl_starts) else '',
                'end': cl_ends[i].strip() if i < len(cl_ends) else '',
                'laid': cl_laids[i].strip() if i < len(cl_laids) else '',
                'slack': cl_slacks[i].strip() if i < len(cl_slacks) else '',
                'remarks': cl_remarks[i].strip() if i < len(cl_remarks) else '',
            })

        # 2. Joint Location Summary
        js_rows = []
        js_nos = request.POST.getlist('ofc_js_no[]')
        js_locs = request.POST.getlist('ofc_js_loc[]')
        js_boxes = request.POST.getlist('ofc_js_box[]')
        js_in_cables = request.POST.getlist('ofc_js_in[]')
        js_out_cables = request.POST.getlist('ofc_js_out[]')
        js_cores = request.POST.getlist('ofc_js_cores[]')
        js_dates = request.POST.getlist('ofc_js_date[]')
        js_splicers = request.POST.getlist('ofc_js_splicer[]')
        for i in range(len(js_nos)):
            js_rows.append({
                'joint_no': js_nos[i].strip() if i < len(js_nos) else '',
                'location': js_locs[i].strip() if i < len(js_locs) else '',
                'box_id': js_boxes[i].strip() if i < len(js_boxes) else '',
                'in_cable': js_in_cables[i].strip() if i < len(js_in_cables) else '',
                'out_cable': js_out_cables[i].strip() if i < len(js_out_cables) else '',
                'cores': js_cores[i].strip() if i < len(js_cores) else '',
                'date': js_dates[i].strip() if i < len(js_dates) else '',
                'splicer': js_splicers[i].strip() if i < len(js_splicers) else '',
            })

        # 3. Jointing / Core Splice Schedule (12 cores)
        sp_rows = []
        sp_in_cables = request.POST.getlist('ofc_sp_in_cable[]')
        sp_in_tubes = request.POST.getlist('ofc_sp_in_tube[]')
        sp_in_cores = request.POST.getlist('ofc_sp_in_core[]')
        sp_out_cables = request.POST.getlist('ofc_sp_out_cable[]')
        sp_out_tubes = request.POST.getlist('ofc_sp_out_tube[]')
        sp_out_cores = request.POST.getlist('ofc_sp_out_core[]')
        sp_losses = request.POST.getlist('ofc_sp_loss[]')
        sp_remarks = request.POST.getlist('ofc_sp_remarks[]')
        for i in range(12):
            sp_rows.append({
                'sl': i + 1,
                'in_cable': sp_in_cables[i].strip() if i < len(sp_in_cables) else '',
                'in_tube': sp_in_tubes[i].strip() if i < len(sp_in_tubes) else '',
                'in_core': sp_in_cores[i].strip() if i < len(sp_in_cores) else '',
                'out_cable': sp_out_cable[i].strip() if i < len(sp_out_cables) and 'sp_out_cable' in locals() else (sp_out_cables[i].strip() if i < len(sp_out_cables) else ''),
                'out_tube': sp_out_tubes[i].strip() if i < len(sp_out_tubes) else '',
                'out_core': sp_out_cores[i].strip() if i < len(sp_out_cores) else '',
                'loss': sp_losses[i].strip() if i < len(sp_losses) else '',
                'remarks': sp_remarks[i].strip() if i < len(sp_remarks) else '',
            })

        # 4. Testing and Acceptance (5 rows total: 4 on Page 1, 1 on Page 2)
        ta_rows = []
        ta_tests = request.POST.getlist('ofc_ta_test[]')
        ta_end_as = request.POST.getlist('ofc_ta_end_a[]')
        ta_end_bs = request.POST.getlist('ofc_ta_end_b[]')
        ta_waves = request.POST.getlist('ofc_ta_wave[]')
        ta_losses = request.POST.getlist('ofc_ta_loss[]')
        ta_results = request.POST.getlist('ofc_ta_result[]')
        for i in range(len(ta_tests)):
            ta_rows.append({
                'test': ta_tests[i].strip() if i < len(ta_tests) else 'OTDR',
                'end_a': ta_end_as[i].strip() if i < len(ta_end_as) else '',
                'end_b': ta_end_bs[i].strip() if i < len(ta_end_bs) else '',
                'wavelength': ta_waves[i].strip() if i < len(ta_waves) else '1310 / 1550 nm',
                'loss': ta_losses[i].strip() if i < len(ta_losses) else '',
                'result': ta_results[i].strip() if i < len(ta_results) else 'Pass',
            })

        general_remarks = request.POST.get('ofc_general_remarks', '').strip()
        additional_findings = general_remarks or additional_findings

        custom_data = {
            'cable_laying': cl_rows,
            'total_cable_laid': request.POST.get('ofc_total_cable_laid', '').strip(),
            'total_slack_reserve': request.POST.get('ofc_total_slack_reserve', '').strip(),
            'joint_summary': js_rows,
            'splice_header': {
                'joint_no': request.POST.get('ofc_sch_joint_no', '').strip(),
                'location': request.POST.get('ofc_sch_location', '').strip(),
                'closure_id': request.POST.get('ofc_sch_closure_id', '').strip(),
                'tray_no': request.POST.get('ofc_sch_tray_no', '').strip(),
            },
            'splice_schedule': sp_rows,
            'testing_acceptance': ta_rows,
            'general_remarks': general_remarks,
        }

    return {
        'attended_by_ids': attended_by_ids,
        'work_request_no': work_request_no,
        'report_date': report_date_str,
        'reported_by': reported_by,
        'contact_no': contact_no,
        'outage_reported_at': outage_reported_at,
        'site_arrival_at': site_arrival_at,
        'restored_at': restored_at,
        'total_downtime': total_downtime,
        'equipment_data': equipment_data,
        'diagnostics_data': diagnostics_data,
        'custom_data': custom_data,
        'fault_selected': fault_selected,
        'action_taken_details': action_taken_details,
        'materials_data': materials_data,
        'faulty_item_disposal': faulty_item_disposal,
        'disposal_ref_no': disposal_ref_no,
        'warranty_status': warranty_status,
        'vendor_po_ref': vendor_po_ref,
        'verification_checks': verification_checks,
        'final_status': final_status,
        'final_status_other': final_status_other,
        'additional_findings': additional_findings,
        'client_ip': client_ip,
    }


def _build_form_context(template_obj, submission=None):
    team_members = TeamMember.objects.filter(is_active=True).order_by('name')

    equipment_fields = []
    for field in template_obj.equipment_fields_schema:
        f_copy = dict(field)
        if submission and submission.equipment_data:
            eq_entry = submission.equipment_data.get(field['key'])
            if isinstance(eq_entry, dict):
                f_copy['current_value'] = eq_entry.get('value', '')
            else:
                f_copy['current_value'] = eq_entry or ''
        else:
            f_copy['current_value'] = ''
        equipment_fields.append(f_copy)

    diagnostic_items = []
    for item in template_obj.diagnostic_items_schema:
        item_copy = dict(item)
        item_id_str = str(item['id'])
        if submission and submission.diagnostics_data and item_id_str in submission.diagnostics_data:
            diag_entry = submission.diagnostics_data[item_id_str]
            item_copy['current_status'] = diag_entry.get('status', 'Yes')
            item_copy['current_remarks'] = diag_entry.get('remarks', '')
        else:
            item_copy['current_status'] = 'Yes'
            item_copy['current_remarks'] = ''
        diagnostic_items.append(item_copy)

    attended_member_ids = []
    if submission:
        attended_member_ids = list(submission.attended_by.values_list('id', flat=True))

    ofc_data = {}
    if template_obj.is_ofc:
        custom_d = submission.custom_data if (submission and submission.custom_data) else {}
        cl_rows = custom_d.get('cable_laying', [])
        if not cl_rows:
            cl_rows = [{'sl': i + 1, 'drum': '', 'from': '', 'to': '', 'path': 'Duct', 'start': '', 'end': '', 'laid': '', 'slack': '', 'remarks': ''} for i in range(3)]

        js_rows = custom_d.get('joint_summary', [])
        if not js_rows:
            js_rows = [{'joint_no': f'J-{i+1:02d}', 'location': '', 'box_id': '', 'in_cable': '', 'out_cable': '', 'cores': '', 'date': '', 'splicer': ''} for i in range(3)]

        sp_rows = custom_d.get('splice_schedule', [])
        if not sp_rows:
            sp_rows = [{'sl': i + 1, 'in_cable': '', 'in_tube': '', 'in_core': '', 'out_cable': '', 'out_tube': '', 'out_core': '', 'loss': '', 'remarks': ''} for i in range(12)]

        ta_rows = custom_d.get('testing_acceptance', [])
        if not ta_rows:
            ta_rows = [{'test': 'OTDR', 'end_a': '', 'end_b': '', 'wavelength': '1310 / 1550 nm', 'loss': '', 'result': 'Pass'} for _ in range(5)]

        ofc_data = {
            'cable_laying': cl_rows,
            'total_cable_laid': custom_d.get('total_cable_laid', ''),
            'total_slack_reserve': custom_d.get('total_slack_reserve', ''),
            'joint_summary': js_rows,
            'splice_header': custom_d.get('splice_header', {'joint_no': 'J-01', 'location': '', 'closure_id': '', 'tray_no': 'Tray 01'}),
            'splice_schedule': sp_rows,
            'testing_acceptance': ta_rows,
            'general_remarks': custom_d.get('general_remarks', submission.additional_findings if submission else ''),
        }

    return {
        'template': template_obj,
        'team_members': team_members,
        'equipment_fields': equipment_fields,
        'diagnostic_items': diagnostic_items,
        'attended_member_ids': attended_member_ids,
        'submission': submission,
        'is_edit': bool(submission),
        'today': timezone.now().strftime('%Y-%m-%d'),
        'ofc_data': ofc_data,
    }


def checklist_form(request, template_id):
    """
    Interactive online form for any of the 12 BIFPCL Word Checklists.
    Renders dynamic equipment fields, Yes/No/NA diagnostic checklist,
    fault classification, spares, and restoration verification.
    """
    template_obj = get_object_or_404(ChecklistTemplate, id=template_id, is_active=True)

    if request.method == 'POST':
        data = _extract_submission_data(request, template_obj)
        attended_by_ids = data.pop('attended_by_ids')

        if not attended_by_ids:
            messages.error(request, "Please select at least one IT team member who Attended this checklist.")
            return redirect('checklist_form', template_id=template_id)

        submission = ChecklistSubmission.objects.create(
            template=template_obj,
            status='SUBMITTED',
            **data
        )
        submission.attended_by.set(attended_by_ids)

        messages.success(request, f"Checklist submitted successfully! Tracking Reference: {submission.tracking_no}")
        return redirect('submission_success', tracking_no=submission.tracking_no)

    context = _build_form_context(template_obj)
    return render(request, 'checklists/checklist_form.html', context)


def checklist_edit(request, submission_id):
    """
    Allow IT team member to edit and resubmit a checklist that was RETURNED by a supervisor/manager.
    """
    submission = get_object_or_404(
        ChecklistSubmission.objects.select_related('template', 'supervised_by', 'approved_by').prefetch_related('attended_by'),
        id=submission_id
    )

    if submission.status != 'RETURNED':
        messages.warning(
            request,
            f"Checklist {submission.tracking_no} cannot be edited because its current status is {submission.get_status_display()}. Only returned checklists can be edited."
        )
        return redirect('checklist_detail', submission_id=submission.id)

    template_obj = submission.template

    if request.method == 'POST':
        data = _extract_submission_data(request, template_obj)
        attended_by_ids = data.pop('attended_by_ids')

        if not attended_by_ids:
            messages.error(request, "Please select at least one IT team member who Attended this checklist.")
            return redirect('checklist_edit', submission_id=submission.id)

        # Update all fields on the existing submission
        for field_name, val in data.items():
            setattr(submission, field_name, val)

        # Reset status back to SUBMITTED for Supervisor review
        submission.status = 'SUBMITTED'
        submission.supervised_by = None
        submission.supervised_at = None
        submission.submitted_at = timezone.now()
        submission.save()
        submission.attended_by.set(attended_by_ids)

        messages.success(
            request,
            f"Checklist {submission.tracking_no} has been successfully updated and resubmitted for Supervisor review!"
        )
        return redirect('submission_success', tracking_no=submission.tracking_no)

    context = _build_form_context(template_obj, submission=submission)
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
