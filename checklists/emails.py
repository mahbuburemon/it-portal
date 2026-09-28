import os
import logging
import threading
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth.models import User
from django.urls import reverse

logger = logging.getLogger(__name__)


def _format_date(val):
    """Format a date object or string safely to DD-MM-YYYY."""
    if not val:
        return '—'
    if hasattr(val, 'strftime'):
        return val.strftime('%d-%m-%Y')
    val_str = str(val).strip()
    # Check if ISO date string (YYYY-MM-DD)
    if len(val_str) == 10 and val_str[4] == '-' and val_str[7] == '-':
        parts = val_str.split('-')
        return f"{parts[2]}-{parts[1]}-{parts[0]}"
    return val_str


def _format_datetime(val):
    """Format a datetime object or string safely."""
    if not val:
        return '—'
    if hasattr(val, 'strftime'):
        return val.strftime('%d-%m-%Y %I:%M %p')
    return str(val)


def _send_email_async(subject, text_content, html_content, recipient_list, sync=False):
    """Internal helper to dispatch email asynchronously in a background thread or synchronously during test."""
    if not recipient_list:
        logger.warning("No recipient email addresses found for notification.")
        return

    def _task():
        try:
            from_email = settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=recipient_list,
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send(fail_silently=False)
            logger.info("Email notification '%s' successfully sent to %s", subject, recipient_list)
        except Exception as ex:
            logger.error("Failed to send email '%s' to %s: %s", subject, recipient_list, ex, exc_info=True)

    if sync or getattr(settings, 'EMAIL_BACKEND', '').endswith('locmem.EmailBackend'):
        _task()
    else:
        thread = threading.Thread(target=_task, daemon=True)
        thread.start()


def get_base_url(request=None):
    """Resolve base domain URL for clickable email links."""
    if request:
        return request.build_absolute_uri('/').rstrip('/')
    portal_host = os.getenv('PORTAL_HOST_URL', '')
    if portal_host:
        return portal_host.rstrip('/')
    return 'http://127.0.0.1:8000'


def send_submission_notification_to_supervisors(submission, request=None):
    """
    Triggered when an attendee submits a new checklist form.
    Notifies all active Supervisors with a direct review link.
    """
    try:
        # 1. Fetch Supervisor Emails
        supervisors = User.objects.filter(groups__name='Supervisor', is_active=True).exclude(email='')
        recipient_list = [u.email.strip() for u in supervisors if u.email.strip()]

        # Allow optional override from env if configured
        override_emails = os.getenv('SUPERVISOR_NOTIFICATION_EMAILS', '')
        if override_emails:
            recipient_list = [e.strip() for e in override_emails.split(',') if e.strip()]

        if not recipient_list:
            logger.warning("No supervisor email found to send submission notification for %s", submission.tracking_no)
            return

        base_url = get_base_url(request)
        review_url = f"{base_url}{reverse('supervisor_review', args=[submission.id])}"
        view_url = f"{base_url}{reverse('checklist_detail', args=[submission.id])}"

        attendees = ", ".join([f"{m.name} ({m.designation})" for m in submission.attended_by.all()]) or "IT Personnel"
        template_title = submission.template.title
        doc_no = submission.template.doc_no
        report_date_disp = _format_date(submission.report_date)

        subject = f"[BIFPCL IT Portal] New Checklist Awaiting Review: {submission.tracking_no} - {template_title}"

        # Plain text version
        text_content = f"""
BANGLADESH-INDIA FRIENDSHIP POWER COMPANY (PVT.) LIMITED
IT Department Operational Checklists Portal

ATTN: Shift IT Supervisor,

A new IT checklist report has been submitted by the IT attendee(s) and is currently awaiting your review and forwarding.

CHECKLIST DETAILS:
- Document: {doc_no} - {template_title}
- Tracking Reference: {submission.tracking_no}
- Job ID / Work Request: {submission.work_request_no or 'N/A'}
- Record / Report Date: {report_date_disp}
- Attended By: {attendees}
{f"- Outage / Downtime: {submission.total_downtime}" if submission.total_downtime else ""}

Please log in to review the report details and forward to Management Approval queue:
{review_url}

Public View Reference:
{view_url}

--
BIFPCL IT Checklists System
Automatic System Notification • Please do not reply directly to this email.
""".strip()

        # Rich HTML version
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f1f5f9; color: #1e293b; margin: 0; padding: 20px; }}
  .container {{ max-width: 620px; margin: 0 auto; background: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #cbd5e1; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
  .header {{ background: #0d3b66; color: #ffffff; padding: 22px 25px; text-align: center; border-bottom: 4px solid #008751; }}
  .header h1 {{ margin: 0; font-size: 17px; font-weight: 700; letter-spacing: 0.5px; }}
  .header p {{ margin: 4px 0 0 0; font-size: 12px; color: #cbd5e1; }}
  .body-content {{ padding: 25px; }}
  .badge {{ display: inline-block; background-color: #e0f2fe; color: #0369a1; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; margin-bottom: 12px; }}
  .title-alert {{ font-size: 16px; font-weight: 700; color: #0d3b66; margin-bottom: 16px; }}
  table.info-table {{ width: 100%; border-collapse: collapse; margin-bottom: 22px; font-size: 13px; }}
  table.info-table th, table.info-table td {{ padding: 8px 12px; border: 1px solid #e2e8f0; text-align: left; }}
  table.info-table th {{ background-color: #f8fafc; color: #475569; width: 35%; font-weight: 600; }}
  table.info-table td {{ color: #0f172a; }}
  .btn-wrapper {{ text-align: center; margin: 25px 0 15px 0; }}
  .btn {{ background-color: #008751; color: #ffffff !important; text-decoration: none; padding: 12px 26px; font-weight: 700; font-size: 13px; border-radius: 25px; display: inline-block; letter-spacing: 0.3px; }}
  .footer {{ background: #f8fafc; padding: 15px 25px; border-top: 1px solid #e2e8f0; font-size: 11px; color: #64748b; text-align: center; line-height: 1.5; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>BANGLADESH-INDIA FRIENDSHIP POWER COMPANY (PVT.) LIMITED</h1>
    <p>IT Department Checklists &amp; Audit Portal</p>
  </div>
  <div class="body-content">
    <div class="badge">Stage 2: Supervisor Review Required</div>
    <div class="title-alert">New Checklist Report Submitted</div>
    <p style="font-size: 13px; line-height: 1.5; margin-bottom: 18px; color: #334155;">
      A new IT report has been submitted by the attending IT team member(s). As a Shift IT Supervisor, please inspect the details and forward the checklist to the Assistant / Deputy Manager for final sign-off.
    </p>

    <table class="info-table">
      <tr>
        <th>Document No.</th>
        <td><strong>{doc_no}</strong></td>
      </tr>
      <tr>
        <th>Form Title</th>
        <td>{template_title}</td>
      </tr>
      <tr>
        <th>Tracking Reference</th>
        <td style="font-family: monospace; font-weight: 700; color: #008751;">{submission.tracking_no}</td>
      </tr>
      <tr>
        <th>Job ID / Work Request</th>
        <td style="font-family: monospace;">{submission.work_request_no or '—'}</td>
      </tr>
      <tr>
        <th>Record / Report Date</th>
        <td>{report_date_disp}</td>
      </tr>
      <tr>
        <th>Attended By</th>
        <td>{attendees}</td>
      </tr>
      {f'<tr><th>Total Downtime</th><td style="color: #dc2626; font-weight: 600;">{submission.total_downtime}</td></tr>' if submission.total_downtime else ''}
    </table>

    <div class="btn-wrapper">
      <a href="{review_url}" class="btn">Review &amp; Forward Checklist &rarr;</a>
    </div>
    <div style="text-align: center; margin-top: 6px;">
      <a href="{view_url}" style="font-size: 11px; color: #0369a1; text-decoration: none;">View Read-Only Checklist Page</a>
    </div>
  </div>
  <div class="footer">
    This is an automated workflow notification from BIFPCL Maitree Super Thermal Power Project IT Portal.<br>
    © 2026 Bangladesh-India Friendship Power Company (Pvt.) Limited. All rights reserved.
  </div>
</div>
</body>
</html>
""".strip()

        _send_email_async(subject, text_content, html_content, recipient_list)
    except Exception as exc:
        logger.error("Error generating supervisor email notification: %s", exc, exc_info=True)


def send_forwarded_notification_to_managers(submission, request=None):
    """
    Triggered when a supervisor reviews and forwards a checklist.
    Notifies all active Managers (Assistant / Deputy Manager) with a direct approval link.
    """
    try:
        # 1. Fetch Manager Emails
        managers = User.objects.filter(groups__name='Manager', is_active=True).exclude(email='')
        recipient_list = [u.email.strip() for u in managers if u.email.strip()]

        # Allow optional override from env if configured
        override_emails = os.getenv('MANAGER_NOTIFICATION_EMAILS', '')
        if override_emails:
            recipient_list = [e.strip() for e in override_emails.split(',') if e.strip()]

        if not recipient_list:
            logger.warning("No manager email found to send approval notification for %s", submission.tracking_no)
            return

        base_url = get_base_url(request)
        approval_url = f"{base_url}{reverse('manager_approve', args=[submission.id])}"
        view_url = f"{base_url}{reverse('checklist_detail', args=[submission.id])}"

        attendees = ", ".join([f"{m.name} ({m.designation})" for m in submission.attended_by.all()]) or "IT Personnel"
        template_title = submission.template.title
        doc_no = submission.template.doc_no
        supervised_by = submission.supervised_by_display
        supervised_at = _format_datetime(submission.supervised_at) if submission.supervised_at else 'Just now'
        remarks = submission.supervisor_remarks or 'None (Standard endorsement)'

        subject = f"[BIFPCL IT Portal] Checklist Forwarded for Final Approval: {submission.tracking_no} - {template_title}"

        # Plain text version
        text_content = f"""
BANGLADESH-INDIA FRIENDSHIP POWER COMPANY (PVT.) LIMITED
IT Department Operational Checklists Portal

ATTN: Assistant Manager / Deputy Manager,

An IT checklist report has been officially reviewed and forwarded by Shift IT Supervisor ({supervised_by}) and is currently awaiting your final approval and sign-off.

CHECKLIST DETAILS:
- Document: {doc_no} - {template_title}
- Tracking Reference: {submission.tracking_no}
- Job ID / Work Request: {submission.work_request_no or 'N/A'}
- Supervised By: {supervised_by} ({supervised_at})
- Supervisor Remarks: {remarks}
- Attended By: {attendees}
{f"- Outage / Downtime: {submission.total_downtime}" if submission.total_downtime else ""}

Please log in to review the report and provide final management approval:
{approval_url}

Public View Reference:
{view_url}

--
BIFPCL IT Checklists System
Automatic System Notification • Please do not reply directly to this email.
""".strip()

        # Rich HTML version
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f1f5f9; color: #1e293b; margin: 0; padding: 20px; }}
  .container {{ max-width: 620px; margin: 0 auto; background: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #cbd5e1; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
  .header {{ background: #0d3b66; color: #ffffff; padding: 22px 25px; text-align: center; border-bottom: 4px solid #008751; }}
  .header h1 {{ margin: 0; font-size: 17px; font-weight: 700; letter-spacing: 0.5px; }}
  .header p {{ margin: 4px 0 0 0; font-size: 12px; color: #cbd5e1; }}
  .body-content {{ padding: 25px; }}
  .badge {{ display: inline-block; background-color: #fef3c7; color: #92400e; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; margin-bottom: 12px; }}
  .title-alert {{ font-size: 16px; font-weight: 700; color: #0d3b66; margin-bottom: 16px; }}
  table.info-table {{ width: 100%; border-collapse: collapse; margin-bottom: 22px; font-size: 13px; }}
  table.info-table th, table.info-table td {{ padding: 8px 12px; border: 1px solid #e2e8f0; text-align: left; }}
  table.info-table th {{ background-color: #f8fafc; color: #475569; width: 35%; font-weight: 600; }}
  table.info-table td {{ color: #0f172a; }}
  .supervisor-box {{ background: #f0fdf4; border-left: 4px solid #008751; padding: 12px 16px; margin-bottom: 20px; border-radius: 4px; font-size: 12.5px; }}
  .btn-wrapper {{ text-align: center; margin: 25px 0 15px 0; }}
  .btn {{ background-color: #008751; color: #ffffff !important; text-decoration: none; padding: 12px 26px; font-weight: 700; font-size: 13px; border-radius: 25px; display: inline-block; letter-spacing: 0.3px; }}
  .footer {{ background: #f8fafc; padding: 15px 25px; border-top: 1px solid #e2e8f0; font-size: 11px; color: #64748b; text-align: center; line-height: 1.5; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>BANGLADESH-INDIA FRIENDSHIP POWER COMPANY (PVT.) LIMITED</h1>
    <p>IT Department Checklists &amp; Audit Portal</p>
  </div>
  <div class="body-content">
    <div class="badge">Stage 3: Management Approval Awaiting Sign-off</div>
    <div class="title-alert">Checklist Forwarded for Final Sign-off</div>
    <p style="font-size: 13px; line-height: 1.5; margin-bottom: 18px; color: #334155;">
      Shift IT Supervisor <strong>{supervised_by}</strong> has completed Stage 2 review and forwarded this report for final Assistant Manager / Deputy Manager endorsement.
    </p>

    <div class="supervisor-box">
      <strong>Supervisor Review Endorsement:</strong><br>
      <span style="color: #166534;">{remarks}</span><br>
      <small style="color: #64748b; margin-top: 4px; display: block;">Endorsed on {supervised_at}</small>
    </div>

    <table class="info-table">
      <tr>
        <th>Document No.</th>
        <td><strong>{doc_no}</strong></td>
      </tr>
      <tr>
        <th>Form Title</th>
        <td>{template_title}</td>
      </tr>
      <tr>
        <th>Tracking Reference</th>
        <td style="font-family: monospace; font-weight: 700; color: #008751;">{submission.tracking_no}</td>
      </tr>
      <tr>
        <th>Job ID / Work Request</th>
        <td style="font-family: monospace;">{submission.work_request_no or '—'}</td>
      </tr>
      <tr>
        <th>Attended By</th>
        <td>{attendees}</td>
      </tr>
      {f'<tr><th>Total Downtime</th><td style="color: #dc2626; font-weight: 600;">{submission.total_downtime}</td></tr>' if submission.total_downtime else ''}
    </table>

    <div class="btn-wrapper">
      <a href="{approval_url}" class="btn">Open &amp; Approve Checklist &rarr;</a>
    </div>
    <div style="text-align: center; margin-top: 6px;">
      <a href="{view_url}" style="font-size: 11px; color: #0369a1; text-decoration: none;">View Read-Only Checklist Page</a>
    </div>
  </div>
  <div class="footer">
    This is an automated workflow notification from BIFPCL Maitree Super Thermal Power Project IT Portal.<br>
    © 2026 Bangladesh-India Friendship Power Company (Pvt.) Limited. All rights reserved.
  </div>
</div>
</body>
</html>
""".strip()

        _send_email_async(subject, text_content, html_content, recipient_list)
    except Exception as exc:
        logger.error("Error generating manager email notification: %s", exc, exc_info=True)
