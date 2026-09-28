from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from checklists.models import TeamMember, ChecklistTemplate, ChecklistSubmission
from django.utils import timezone
from django.core import mail


class BIFPCLWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Groups
        self.sup_group = Group.objects.create(name='Supervisor')
        self.mgr_group = Group.objects.create(name='Manager')

        # Users - 3 Supervisors: Sabbir, Swarup, Ramjan
        self.supervisor_sabbir = User.objects.create_user(
            username='sabbir', password='Password123!', first_name='Sabbir', last_name='Ahmen',
            email='sabbir.supervisor@bifpcl.com'
        )
        self.supervisor_sabbir.groups.add(self.sup_group)

        self.supervisor_swarup = User.objects.create_user(
            username='swarup', password='Password123!', first_name='Swarup', last_name='Mohon',
            email='swarup.supervisor@bifpcl.com'
        )
        self.supervisor_swarup.groups.add(self.sup_group)

        self.supervisor_ramjan = User.objects.create_user(
            username='ramjan', password='Password123!', first_name='Ramjan', last_name='Ali',
            email='ramjan.supervisor@bifpcl.com'
        )
        self.supervisor_ramjan.groups.add(self.sup_group)

        # Primary supervisor reference for test cases
        self.supervisor = self.supervisor_sabbir

        # Users - 2 Managers: Assistant Manager Kasad and Deputy Manager Tanvir
        self.asst_manager = User.objects.create_user(
            username='kasad', password='Password123!', first_name='Kasad', last_name='Ullah',
            email='kasad.am@bifpcl.com'
        )
        self.asst_manager.groups.add(self.mgr_group)

        self.deputy_manager = User.objects.create_user(
            username='tanvir', password='Password123!', first_name='Tanvir', last_name='Islam',
            email='tanvir.dm@bifpcl.com'
        )
        self.deputy_manager.groups.add(self.mgr_group)

        # Primary manager reference for test cases
        self.manager = self.asst_manager

        # IT Team Group & Member User (Stage 1 Authentication)
        self.it_group = Group.objects.create(name='IT Team')
        self.member_user = User.objects.create_user(
            username='alamin', password='Password123!', first_name='Md. Al-Amin', last_name='Hossain',
            email='alamin@bifpcl.com'
        )
        self.member_user.groups.add(self.it_group)

        # Team Member Profile
        self.team_member = TeamMember.objects.create(
            user=self.member_user,
            name='Md. Al-Amin Hossain',
            employee_id='IT-EMP-101',
            designation='Senior IT Executive',
            phone='+880 1711-000001',
            email='alamin@bifpcl.com'
        )

        # Default login as IT team member for form submissions
        self.client.login(username='alamin', password='Password123!')

        # Template
        self.template = ChecklistTemplate.objects.create(
            doc_no='BIFPCL/IT/F/01',
            title='CCTV Troubleshooting Report & Checklist',
            category='Surveillance & Security',
            revision='Rev: 00',
            equipment_fields_schema=[
                {'key': 'camera_id', 'label': 'Camera ID / Name', 'required': True},
                {'key': 'location', 'label': 'Location', 'required': True}
            ],
            diagnostic_items_schema=[
                {'id': 1, 'text': 'Correct camera ID and location confirmed'},
                {'id': 2, 'text': 'Camera physically inspected for damage'}
            ],
            fault_options_schema=[
                {'key': 'minor', 'label': '1. Minor issue corrected', 'desc': 'Loose cable'}
            ],
            verification_items_schema=['Camera online and live view stable']
        )

    def test_public_dashboard_accessible_without_login(self):
        """Users can access the public catalog, but unauthenticated users are prompted to log in."""
        self.client.logout()
        response = self.client.get(reverse('main_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'CCTV Troubleshooting Report')
        self.assertContains(response, 'BIFPCL/IT/F/01')
        self.assertContains(response, 'Log In to Access Forms')

    def test_authenticated_checklist_submission_and_personal_dashboard(self):
        """IT Team members must log in to submit forms, and submissions appear on their Personal Dashboard."""
        self.client.login(username='alamin', password='Password123!')

        # 1. Access member personal dashboard
        dash_resp = self.client.get(reverse('member_dashboard'))
        self.assertEqual(dash_resp.status_code, 200)
        self.assertContains(dash_resp, 'Md. Al-Amin Hossain')
        self.assertContains(dash_resp, 'Senior IT Executive')
        self.assertContains(dash_resp, 'IT-EMP-101')

        # 2. Role redirect takes IT members to their personal dashboard
        redir_resp = self.client.get(reverse('role_redirect'))
        self.assertEqual(redir_resp.status_code, 302)
        self.assertEqual(redir_resp.url, reverse('member_dashboard'))

        # 3. Open checklist form - name is auto-preselected
        form_get = self.client.get(reverse('checklist_form', args=[self.template.id]))
        self.assertEqual(form_get.status_code, 200)

        # 4. Submit form
        self.team_member2 = TeamMember.objects.create(
            name='Mohammad Shamim Reza',
            employee_id='IT-EMP-102',
            designation='Assistant IT Engineer'
        )
        post_data = {
            'attended_by': [self.team_member.id, self.team_member2.id],
            'work_request_no': 'WR-999',
            'report_date': '2026-09-23',
            'eq_camera_id': 'CAM-GATE-01',
            'eq_location': 'Main Gate Substation',
            'diag_status_1': 'Yes',
            'diag_remarks_1': 'All clear',
            'diag_status_2': 'Yes',
            'diag_remarks_2': 'No physical damage',
            'fault_selected': 'minor',
            'action_taken_details': 'Reconnected loose PoE cable and tested live stream.',
            'verification_checks': ['Camera online and live view stable'],
            'final_status': 'Restored and Closed',
        }
        response = self.client.post(reverse('checklist_form', args=[self.template.id]), data=post_data)
        self.assertEqual(response.status_code, 302)

        # Verify submission in database has submitted_by set to alamin
        sub = ChecklistSubmission.objects.get(work_request_no='WR-999')
        self.assertEqual(sub.status, 'SUBMITTED')
        self.assertEqual(sub.submitted_by, self.member_user)
        self.assertEqual(sub.attended_by.count(), 2)
        self.assertIn(self.team_member, sub.attended_by.all())
        self.assertIn(self.team_member2, sub.attended_by.all())
        self.assertEqual(sub.equipment_data['camera_id']['value'], 'CAM-GATE-01')
        self.assertIsNone(sub.supervised_by)
        self.assertIsNone(sub.approved_by)

        # 5. Check submission appears on member dashboard
        dash_after = self.client.get(reverse('member_dashboard'))
        self.assertEqual(dash_after.status_code, 200)
        self.assertContains(dash_after, sub.tracking_no)
        self.assertContains(dash_after, 'WR-999')

    def test_rbac_security_boundaries(self):
        """Anonymous users cannot access checklist forms, supervisor queue, or manager queue."""
        self.client.logout()

        # Anonymous access blocked to checklist forms and personal dashboard
        resp_form = self.client.get(reverse('checklist_form', args=[self.template.id]))
        self.assertEqual(resp_form.status_code, 302)
        self.assertIn('/login/', resp_form.url)

        resp_member = self.client.get(reverse('member_dashboard'))
        self.assertEqual(resp_member.status_code, 302)
        self.assertIn('/login/', resp_member.url)

        # Anonymous access blocked to supervisor and manager dashboards
        resp_sup = self.client.get(reverse('supervisor_dashboard'))
        self.assertEqual(resp_sup.status_code, 302)
        self.assertIn('/login/', resp_sup.url)

        resp_mgr = self.client.get(reverse('manager_dashboard'))
        self.assertEqual(resp_mgr.status_code, 302)
        self.assertIn('/login/', resp_mgr.url)

        # Supervisor cannot access Manager dashboard
        self.client.login(username='sabbir', password='Password123!')
        resp_mgr_as_sup = self.client.get(reverse('manager_dashboard'))
        self.assertEqual(resp_mgr_as_sup.status_code, 302)
        self.assertEqual(resp_mgr_as_sup.url, reverse('supervisor_dashboard'))

        # Manager cannot access Supervisor dashboard
        self.client.logout()
        self.client.login(username='kasad', password='Password123!')
        resp_sup_as_mgr = self.client.get(reverse('supervisor_dashboard'))
        self.assertEqual(resp_sup_as_mgr.status_code, 302)
        self.assertEqual(resp_sup_as_mgr.url, reverse('manager_dashboard'))

    def test_end_to_end_approval_workflow(self):
        """
        Full lifecycle test:
        Submitted by IT Members -> Forwarded by Supervisor -> Approved by Manager.
        """
        # 1. Create submission
        sub = ChecklistSubmission.objects.create(
            template=self.template,
            work_request_no='WR-FLOW-1',
            report_date=timezone.now().date(),
            status='SUBMITTED'
        )
        sub.attended_by.add(self.team_member)
        self.assertEqual(sub.status, 'SUBMITTED')

        # 2. Supervisor reviews and forwards
        self.client.login(username='sabbir', password='Password123!')
        forward_resp = self.client.post(
            reverse('supervisor_review', args=[sub.id]),
            data={'action': 'forward', 'supervisor_remarks': 'Checked live feeds, all OK.'}
        )
        self.assertEqual(forward_resp.status_code, 302)

        sub.refresh_from_db()
        self.assertEqual(sub.status, 'FORWARDED')
        self.assertEqual(sub.supervised_by, self.supervisor)
        self.assertIsNotNone(sub.supervised_at)
        self.assertEqual(sub.supervisor_remarks, 'Checked live feeds, all OK.')

        # 3. Manager reviews and gives final approval
        self.client.logout()
        self.client.login(username='kasad', password='Password123!')
        approve_resp = self.client.post(
            reverse('manager_approve', args=[sub.id]),
            data={'action': 'approve', 'manager_remarks': 'Sign-off complete.'}
        )
        self.assertEqual(approve_resp.status_code, 302)

        sub.refresh_from_db()
        self.assertEqual(sub.status, 'APPROVED')
        self.assertEqual(sub.approved_by, self.manager)
        self.assertIsNotNone(sub.approved_at)

        # 4. Print preview contains all signatures
        print_resp = self.client.get(reverse('checklist_print', args=[sub.id]))
        self.assertEqual(print_resp.status_code, 200)
        self.assertContains(print_resp, self.team_member.name)
        self.assertContains(print_resp, self.supervisor.get_full_name())
        self.assertContains(print_resp, self.manager.get_full_name())
        self.assertContains(print_resp, 'BIFPCL/IT/F/01')

    def test_returned_checklist_edit_and_resubmit_workflow(self):
        """
        Test that when a supervisor returns a checklist:
        1. Status is RETURNED.
        2. Dashboard shows 'Edit' button.
        3. Detail page shows 'Edit & Resubmit' button and return alert.
        4. Member opens edit form, updates values, and resubmits.
        5. Status returns to SUBMITTED and awaits supervisor review.
        """
        # 1. Create initial submission
        sub = ChecklistSubmission.objects.create(
            template=self.template,
            work_request_no='WR-CORRECTION-01',
            report_date=timezone.now().date(),
            status='SUBMITTED',
            equipment_data={'camera_id': {'label': 'Camera ID / Name', 'value': 'CAM-WRONG'}, 'location': {'label': 'Location', 'value': 'Gate 1'}},
            diagnostics_data={'1': {'text': 'Item 1', 'status': 'Yes', 'remarks': ''}, '2': {'text': 'Item 2', 'status': 'No', 'remarks': 'Failed'}},
            fault_selected='minor',
            action_taken_details='Initial check done',
            final_status='Pending Replacement'
        )
        sub.attended_by.add(self.team_member)

        # 2. Supervisor returns it for correction
        self.client.login(username='sabbir', password='Password123!')
        return_resp = self.client.post(
            reverse('supervisor_review', args=[sub.id]),
            data={'action': 'return', 'supervisor_remarks': 'Please verify camera tag CAM-GATE-01 and update action taken.'}
        )
        self.assertEqual(return_resp.status_code, 302)
        sub.refresh_from_db()
        self.assertEqual(sub.status, 'RETURNED')
        self.assertEqual(sub.supervisor_remarks, 'Please verify camera tag CAM-GATE-01 and update action taken.')

        # 3. Main dashboard shows Edit button
        self.client.logout()
        dash_resp = self.client.get(reverse('main_dashboard'))
        self.assertEqual(dash_resp.status_code, 200)
        self.assertContains(dash_resp, reverse('checklist_edit', args=[sub.id]))
        self.assertContains(dash_resp, 'Edit')

        # 4. Detail page shows Edit & Resubmit button
        detail_resp = self.client.get(reverse('checklist_detail', args=[sub.id]))
        self.assertEqual(detail_resp.status_code, 200)
        self.assertContains(detail_resp, reverse('checklist_edit', args=[sub.id]))
        self.assertContains(detail_resp, 'Checklist Returned for Correction')
        self.assertContains(detail_resp, 'Please verify camera tag CAM-GATE-01 and update action taken.')

        # 5. Member logs in and accesses the edit form
        self.client.login(username='alamin', password='Password123!')
        edit_resp = self.client.get(reverse('checklist_edit', args=[sub.id]))
        self.assertEqual(edit_resp.status_code, 200)
        self.assertContains(edit_resp, 'CAM-WRONG')
        self.assertContains(edit_resp, 'Please verify camera tag CAM-GATE-01 and update action taken.')
        self.assertContains(edit_resp, 'Save Changes &amp; Resubmit Checklist')

        # 6. Member updates the values and resubmits
        resubmit_data = {
            'attended_by': [self.team_member.id],
            'work_request_no': 'WR-CORRECTION-01',
            'report_date': '2026-09-24',
            'eq_camera_id': 'CAM-GATE-01',
            'eq_location': 'Main Gate Substation',
            'diag_status_1': 'Yes',
            'diag_remarks_1': 'Verified correct',
            'diag_status_2': 'Yes',
            'diag_remarks_2': 'Replaced and operational',
            'fault_selected': 'minor',
            'action_taken_details': 'Replaced camera unit with CAM-GATE-01 and aligned view.',
            'verification_checks': ['Camera online and live view stable'],
            'final_status': 'Restored and Closed',
        }
        post_resp = self.client.post(reverse('checklist_edit', args=[sub.id]), data=resubmit_data)
        self.assertEqual(post_resp.status_code, 302)

        # 7. Verify submission is back to SUBMITTED and pending supervisor
        sub.refresh_from_db()
        self.assertEqual(sub.status, 'SUBMITTED')
        self.assertIsNone(sub.supervised_by)
        self.assertIsNone(sub.supervised_at)
        self.assertEqual(sub.equipment_data['camera_id']['value'], 'CAM-GATE-01')
        self.assertEqual(sub.action_taken_details, 'Replaced camera unit with CAM-GATE-01 and aligned view.')

        # 8. Check that non-returned checklist cannot be edited
        forbidden_edit_resp = self.client.get(reverse('checklist_edit', args=[sub.id]))
        self.assertEqual(forbidden_edit_resp.status_code, 302)
        self.assertEqual(forbidden_edit_resp.url, reverse('checklist_detail', args=[sub.id]))

    def test_optional_remarks_in_review_and_approval(self):
        """
        Supervisor and Manager should be able to submit review and approval
        without entering any remarks or comments (both fields are optional).
        """
        sub = ChecklistSubmission.objects.create(
            template=self.template,
            work_request_no='WR-OPTIONAL-REMARKS',
            report_date=timezone.now().date(),
            status='SUBMITTED'
        )
        sub.attended_by.add(self.team_member)

        # 1. Supervisor forwards without remarks
        self.client.login(username='sabbir', password='Password123!')
        review_page = self.client.get(reverse('supervisor_review', args=[sub.id]))
        self.assertEqual(review_page.status_code, 200)
        self.assertContains(review_page, '(Optional)')
        self.assertNotContains(review_page, 'id="id_supervisor_remarks" rows="4" class="form-control" placeholder="Verified camera feeds restored and latency within tolerance. Forwarded for management sign-off." required')

        forward_resp = self.client.post(
            reverse('supervisor_review', args=[sub.id]),
            data={'action': 'forward', 'supervisor_remarks': ''}
        )
        self.assertEqual(forward_resp.status_code, 302)
        sub.refresh_from_db()
        self.assertEqual(sub.status, 'FORWARDED')
        self.assertEqual(sub.supervisor_remarks, '')
        self.assertEqual(sub.supervised_by, self.supervisor)

        # 2. Manager approves without remarks
        self.client.logout()
        self.client.login(username='kasad', password='Password123!')
        approval_page = self.client.get(reverse('manager_approve', args=[sub.id]))
        self.assertEqual(approval_page.status_code, 200)
        self.assertContains(approval_page, '(Optional)')
        self.assertNotContains(approval_page, 'id="id_manager_remarks" rows="3" class="form-control" placeholder="Verified and approved for permanent archival." required')

        approve_resp = self.client.post(
            reverse('manager_approve', args=[sub.id]),
            data={'action': 'approve', 'manager_remarks': ''}
        )
        self.assertEqual(approve_resp.status_code, 302)
        sub.refresh_from_db()
        self.assertEqual(sub.status, 'APPROVED')
        self.assertEqual(sub.manager_remarks, '')
        self.assertEqual(sub.approved_by, self.manager)

    def test_form_02_new_cctv_installation_workflow(self):
        """Test Form 02 (New CCTV Installation Report & Checklist) lifecycle."""
        t2 = ChecklistTemplate.objects.create(
            doc_no='BIFPCL/IT/F/02',
            title='New CCTV Installation Report & Checklist',
            category='Surveillance & Physical Security',
            revision='Rev: 00',
            equipment_fields_schema=[
                {'key': 'camera_id_1', 'label': 'Camera ID / Name 1', 'required': True},
                {'key': 'location_1', 'label': 'Location', 'required': True},
                {'key': 'camera_model', 'label': 'Camera Model', 'required': True},
                {'key': 'serial_no', 'label': 'Serial No.', 'required': True},
            ],
            diagnostic_items_schema=[
                {'id': 1, 'text': 'Proper alignment'},
                {'id': 2, 'text': 'Proper focus'},
            ],
            fault_options_schema=[],
            verification_items_schema=[
                'Both VMS servers configured, if applicable',
                'Camera online and live view stable',
            ]
        )

        # 1. Load form
        resp = self.client.get(reverse('checklist_form', args=[t2.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Job ID')
        self.assertContains(resp, 'Installation Date')
        self.assertContains(resp, 'Physical Installation Checklist')
        self.assertContains(resp, 'Post Installation Verification')

        # 2. Submit form
        post_data = {
            'attended_by': [self.team_member.id],
            'work_request_no': 'BIFPCL/IT/CCTV/INS/2026/001',
            'report_date': '2026-09-27',
            'eq_camera_id_1': 'CAM-GATE-02',
            'eq_location_1': 'Main Sentry Gate North',
            'eq_camera_model': 'Hikvision DS-2CD2T87G2-L',
            'eq_serial_no': 'SN-8923478912',
            'diag_status_1': 'Yes',
            'diag_remarks_1': 'Aligned to main gate',
            'diag_status_2': 'Yes',
            'diag_remarks_2': 'Clear image',
            'mat_desc[]': ['Cat6 Cable'],
            'mat_model[]': ['Cat6 UTP'],
            'mat_qty[]': ['40m'],
            'mat_ref[]': ['SIR-102'],
            'warranty_status': 'Under Warranty',
            'vendor_po_ref': 'PO-88',
            'verification_checks': ['Both VMS servers configured, if applicable', 'Camera online and live view stable'],
            'final_status': 'Commissioned & Closed',
        }
        submit_resp = self.client.post(reverse('checklist_form', args=[t2.id]), data=post_data)
        self.assertEqual(submit_resp.status_code, 302)

        sub = ChecklistSubmission.objects.get(work_request_no='BIFPCL/IT/CCTV/INS/2026/001')
        self.assertEqual(sub.status, 'SUBMITTED')
        self.assertEqual(sub.template, t2)

        # 3. Print view
        print_resp = self.client.get(reverse('checklist_print', args=[sub.id]))
        self.assertEqual(print_resp.status_code, 200)
        self.assertContains(print_resp, 'Job ID')
        self.assertContains(print_resp, 'Physical Installation Checklist')
        self.assertContains(print_resp, 'Commissioned &amp; Closed')

    def test_form_03_cctv_replacement_workflow(self):
        """Test CCTV Replacement Checklist (F/03) with disposal and dynamic labels."""
        t3 = ChecklistTemplate.objects.create(
            doc_no='BIFPCL/IT/F/03',
            title='CCTV Replacement Report & Checklist',
            category='Surveillance',
            revision='Rev: 00',
            retention_period='3 Years',
            equipment_fields_schema=[
                {'key': 'camera_id_1', 'label': 'Camera ID / Name 1', 'required': True},
                {'key': 'damaged_camera_model', 'label': 'Damaged Camera Model', 'required': True},
                {'key': 'replacing_camera_model', 'label': 'Replacing Camera Model', 'required': True},
                {'key': 'height_work_ppe', 'label': 'Height Work / PPE', 'options': ['Height work', 'PPE used', 'Not applicable']},
            ],
            diagnostic_items_schema=[
                {'id': 1, 'text': 'Proper alignment'},
            ],
            fault_options_schema=[],
            verification_items_schema=['Camera online and live view stable'],
        )
        self.assertEqual(t3.job_id_label, 'Job ID')
        self.assertEqual(t3.date_label, 'Date')
        self.assertEqual(t3.physical_heading, 'Physical Installation Checklist')
        self.assertEqual(t3.verification_heading, 'Post Replacement Verification')
        self.assertTrue(t3.has_disposal)

        post_data = {
            'attended_by': [self.team_member.id],
            'work_request_no': 'BIFPCL/IT/CCTV/REP/2026/012',
            'report_date': '2026-09-27',
            'eq_camera_id_1': 'CAM-GATE-01',
            'eq_damaged_camera_model': 'DS-2CD2T47G1-L',
            'eq_replacing_camera_model': 'DS-2CD2T87G2-L',
            'eq_height_work_ppe': 'PPE used',
            'diag_status_1': 'Yes',
            'faulty_item_disposal': 'Store Return',
            'disposal_ref_no': 'SRN-552',
            'warranty_status': 'Under AMC',
            'vendor_po_ref': 'PO-991',
            'verification_checks': ['Camera online and live view stable'],
            'final_status': 'Restored and Closed',
        }
        resp = self.client.post(reverse('checklist_form', args=[t3.id]), data=post_data)
        self.assertEqual(resp.status_code, 302)

        sub = ChecklistSubmission.objects.get(work_request_no='BIFPCL/IT/CCTV/REP/2026/012')
        self.assertEqual(sub.status, 'SUBMITTED')

        print_resp = self.client.get(reverse('checklist_print', args=[sub.id]))
        self.assertEqual(print_resp.status_code, 200)
        self.assertContains(print_resp, 'Post Replacement Verification')
        self.assertContains(print_resp, 'Faulty Item Disposal')
        self.assertContains(print_resp, 'Store Return')

    def test_form_04_ap_troubleshooting_workflow(self):
        """Test AP Troubleshooting Checklist (F/04) with outage tracking and fault classification."""
        t4 = ChecklistTemplate.objects.create(
            doc_no='BIFPCL/IT/F/04',
            title='AP Troubleshooting Report & Checklist',
            category='Network',
            revision='Rev: 00',
            retention_period='3 Years',
            equipment_fields_schema=[
                {'key': 'ap_id_name', 'label': 'AP ID / Name', 'required': True},
                {'key': 'location', 'label': 'Location', 'required': True},
            ],
            diagnostic_items_schema=[
                {'id': 1, 'text': 'Correct AP ID and location confirmed'},
            ],
            fault_options_schema=[
                {'key': 'minor_issue', 'label': '1. Minor issue corrected', 'desc': 'Loose cable'},
            ],
            verification_items_schema=['AP online in controller'],
        )
        self.assertEqual(t4.job_id_label, 'Work Request No.')
        self.assertEqual(t4.date_label, 'Report Date')
        self.assertTrue(t4.has_outage_tracking)
        self.assertEqual(t4.verification_heading, 'Restoration Verification')

        post_data = {
            'attended_by': [self.team_member.id],
            'work_request_no': 'WR-AP-2026-004',
            'report_date': '2026-09-27',
            'eq_ap_id_name': 'AP-ADMIN-01',
            'eq_location': 'Admin 2nd Floor',
            'outage_reported_at': '2026-09-27T08:00',
            'site_arrival_at': '2026-09-27T08:15',
            'restored_at': '2026-09-27T09:00',
            'total_downtime': '1h 00m',
            'reported_by': 'Admin Officer',
            'contact_no': '2100',
            'diag_status_1': 'Yes',
            'fault_selected': 'minor_issue',
            'action_taken_details': 'PoE cable reseated on patch panel',
            'faulty_item_disposal': 'N/A',
            'warranty_status': 'Under Warranty',
            'verification_checks': ['AP online in controller'],
            'final_status': 'Restored and Closed',
        }
        resp = self.client.post(reverse('checklist_form', args=[t4.id]), data=post_data)
        self.assertEqual(resp.status_code, 302)

        sub = ChecklistSubmission.objects.get(work_request_no='WR-AP-2026-004')
        self.assertEqual(sub.status, 'SUBMITTED')
        self.assertEqual(sub.total_downtime, '1h 00m')

    def test_form_05_new_ap_installation_workflow(self):
        """Test New AP Installation Checklist (F/05) with dynamic option fields."""
        t5 = ChecklistTemplate.objects.create(
            doc_no='BIFPCL/IT/F/05',
            title='New AP Installation Report & Checklist',
            category='Network',
            revision='Rev: 00',
            retention_period='3 Years',
            equipment_fields_schema=[
                {'key': 'ap_id_name', 'label': 'AP ID / Name', 'required': True},
                {'key': 'mounting_type', 'label': 'Mounting Type', 'options': ['Ceiling', 'Wall', 'Pole', 'Other']},
                {'key': 'power_source', 'label': 'Power Source', 'options': ['PoE Switch', 'Injector', 'Adapter']},
            ],
            diagnostic_items_schema=[
                {'id': 1, 'text': 'AP mounted securely with correct orientation'},
            ],
            fault_options_schema=[],
            verification_items_schema=['AP online in controller', 'SSID broadcast and authentication verified'],
        )
        self.assertEqual(t5.job_id_label, 'Job ID')
        self.assertEqual(t5.date_label, 'Installation Date')
        self.assertEqual(t5.physical_heading, 'Physical Installation Checklist')
        self.assertEqual(t5.verification_heading, 'Post Installation Verification')
        self.assertFalse(t5.has_disposal)

        post_data = {
            'attended_by': [self.team_member.id],
            'work_request_no': 'BIFPCL/IT/AP/INS/2026/001',
            'report_date': '2026-09-27',
            'eq_ap_id_name': 'AP-PLANT-04',
            'eq_mounting_type': 'Ceiling',
            'eq_power_source': 'PoE Switch',
            'diag_status_1': 'Yes',
            'mat_desc[]': ['Patch cord 2m'],
            'mat_model[]': ['Cat6 UTP'],
            'mat_qty[]': ['1'],
            'mat_ref[]': ['SR-88'],
            'warranty_status': 'Under Warranty',
            'vendor_po_ref': 'PO-CISC-2026',
            'verification_checks': ['AP online in controller', 'SSID broadcast and authentication verified'],
            'final_status': 'Commissioned & Closed',
        }
        resp = self.client.post(reverse('checklist_form', args=[t5.id]), data=post_data)
        self.assertEqual(resp.status_code, 302)

        sub = ChecklistSubmission.objects.get(work_request_no='BIFPCL/IT/AP/INS/2026/001')
        self.assertEqual(sub.status, 'SUBMITTED')

        # Verify formatted equipment fields
        fields = sub.formatted_equipment_fields
        self.assertEqual(len(fields), 3)
        self.assertEqual(fields[1]['value'], 'Ceiling')
        self.assertEqual(fields[2]['value'], 'PoE Switch')

    def test_form_06_ap_replacement_workflow(self):
        """Test AP Replacement Checklist (F/06)"""
        t6 = ChecklistTemplate.objects.create(
            doc_no='BIFPCL/IT/F/06',
            title='AP Replacement Report & Checklist',
            category='Network',
            revision='Rev: 00',
            retention_period='3 Years',
            equipment_fields_schema=[
                {'key': 'ap_id_name', 'label': 'AP ID / Name', 'required': True},
                {'key': 'damaged_ap_model', 'label': 'Damaged AP Model', 'required': True},
                {'key': 'replacing_ap_model', 'label': 'Replacing AP Model', 'required': True},
                {'key': 'height_work_ppe', 'label': 'Height Work / PPE', 'options': ['Height work', 'PPE used', 'Not applicable']},
            ],
            diagnostic_items_schema=[
                {'id': 1, 'text': 'Proper AP mounting'},
            ],
            fault_options_schema=[],
            verification_items_schema=['WiFi signal OK', 'WiFi speed OK'],
        )
        self.assertEqual(t6.job_id_label, 'Job ID')
        self.assertEqual(t6.date_label, 'Date')
        self.assertEqual(t6.default_job_id, 'BIFPCL/IT/AP/REP/2026/')
        self.assertTrue(t6.has_disposal)
        self.assertEqual(t6.verification_heading, 'Post Replacement Verification')

        post_data = {
            'attended_by': [self.team_member.id],
            'work_request_no': 'BIFPCL/IT/AP/REP/2026/005',
            'report_date': '2026-09-27',
            'eq_ap_id_name': 'AP-ADMIN-02',
            'eq_damaged_ap_model': 'Cisco 2802I',
            'eq_replacing_ap_model': 'Cisco 9120AXI',
            'eq_height_work_ppe': 'Height work',
            'diag_status_1': 'Yes',
            'faulty_item_disposal': 'Store Return',
            'disposal_ref_no': 'SR-412',
            'warranty_status': 'Under Warranty',
            'verification_checks': ['WiFi signal OK', 'WiFi speed OK'],
            'final_status': 'Restored and Closed',
        }
        resp = self.client.post(reverse('checklist_form', args=[t6.id]), data=post_data)
        self.assertEqual(resp.status_code, 302)

        sub = ChecklistSubmission.objects.get(work_request_no='BIFPCL/IT/AP/REP/2026/005')
        self.assertEqual(sub.status, 'SUBMITTED')

        print_resp = self.client.get(reverse('checklist_print', args=[sub.id]))
        self.assertEqual(print_resp.status_code, 200)
        self.assertContains(print_resp, 'Post Replacement Verification')

    def test_form_07_telephone_troubleshooting_workflow(self):
        """Test Telephone Troubleshooting Checklist (F/07)"""
        t7 = ChecklistTemplate.objects.create(
            doc_no='BIFPCL/IT/F/07',
            title='Telephone Troubleshooting Report & Checklist',
            category='Telecommunications & EPABX',
            revision='Rev: 00',
            retention_period='3 Years',
            equipment_fields_schema=[
                {'key': 'extension_no', 'label': 'Extension No.', 'required': True},
                {'key': 'phone_type', 'label': 'Phone Type', 'options': ['Analog', 'IP', 'DECT', 'Hotline']},
            ],
            diagnostic_items_schema=[
                {'id': 1, 'text': 'Correct extension number and location confirmed'},
            ],
            fault_options_schema=[
                {'key': 'minor_issue', 'label': '1. Minor issue corrected', 'desc': 'Loose cord'},
            ],
            verification_items_schema=['Dial tone available', 'Outgoing call tested'],
        )
        self.assertEqual(t7.job_id_label, 'Work Request No.')
        self.assertEqual(t7.date_label, 'Report Date')
        self.assertTrue(t7.has_outage_tracking)
        self.assertIn('Pending EPABX Vendor', t7.final_status_choices)

        post_data = {
            'attended_by': [self.team_member.id],
            'work_request_no': 'WR-TEL-2026-001',
            'report_date': '2026-09-27',
            'eq_extension_no': '2104',
            'eq_phone_type': 'Analog',
            'diag_status_1': 'Yes',
            'fault_selected': 'minor_issue',
            'action_taken_details': 'Line cord replaced',
            'warranty_status': 'Out of Warranty',
            'verification_checks': ['Dial tone available'],
            'final_status': 'Restored and Closed',
        }
        resp = self.client.post(reverse('checklist_form', args=[t7.id]), data=post_data)
        self.assertEqual(resp.status_code, 302)

        sub = ChecklistSubmission.objects.get(work_request_no='WR-TEL-2026-001')
        self.assertEqual(sub.status, 'SUBMITTED')

    def test_form_08_and_09_telephone_installation_and_replacement(self):
        """Test Telephone Installation (F/08) and Replacement (F/09)"""
        t8 = ChecklistTemplate.objects.create(
            doc_no='BIFPCL/IT/F/08',
            title='New Telephone Installation Report & Checklist',
            category='Telecommunications & EPABX',
            revision='Rev: 00',
            retention_period='3 Years',
            equipment_fields_schema=[
                {'key': 'extension_no', 'label': 'Extension No.', 'required': True},
            ],
            diagnostic_items_schema=[{'id': 1, 'text': 'Cable laid properly'}],
            fault_options_schema=[],
            verification_items_schema=['Dial tone available'],
        )
        self.assertEqual(t8.default_job_id, 'BIFPCL/IT/TEL/INS/2026/')
        self.assertFalse(t8.has_disposal)
        self.assertIn('Pending Cable Work', t8.final_status_choices)

        t9 = ChecklistTemplate.objects.create(
            doc_no='BIFPCL/IT/F/09',
            title='Telephone Replacement Report & Checklist',
            category='Telecommunications & EPABX',
            revision='Rev: 00',
            retention_period='3 Years',
            equipment_fields_schema=[
                {'key': 'extension_no', 'label': 'Extension No.', 'required': True},
            ],
            diagnostic_items_schema=[{'id': 1, 'text': 'Damaged instrument removed'}],
            fault_options_schema=[],
            verification_items_schema=['Dial tone available'],
        )
        self.assertEqual(t9.default_job_id, 'BIFPCL/IT/TEL/REP/2026/')
        self.assertTrue(t9.has_disposal)
        self.assertIn('Pending EPABX Configuration', t9.final_status_choices)

    def test_form_10_desktop_laptop_troubleshooting_workflow(self):
        """Test Desktop / Laptop Troubleshooting Checklist (F/10)"""
        t10 = ChecklistTemplate.objects.create(
            doc_no='BIFPCL/IT/F/10',
            title='Desktop / Laptop Troubleshooting Report & Checklist',
            category='End-User Computing & Workstations',
            revision='Rev: 00',
            retention_period='3 Years',
            equipment_fields_schema=[
                {'key': 'asset_tag_no', 'label': 'Asset / Tag No.', 'required': True},
                {'key': 'equipment_type', 'label': 'Equipment Type', 'options': ['Desktop', 'Laptop', 'AIO', 'Other']},
            ],
            diagnostic_items_schema=[
                {'id': 1, 'text': 'Fault reported by user confirmed and reproduced'},
            ],
            fault_options_schema=[
                {'key': 'minor_issue', 'label': '1. Minor issue corrected', 'desc': 'Loose cable'},
            ],
            verification_items_schema=['System boots and runs normally'],
        )
        self.assertEqual(t10.job_id_label, 'Work Request No.')
        self.assertEqual(t10.date_label, 'Report Date')
        self.assertEqual(t10.outage_reported_label, 'Fault Reported At')
        self.assertEqual(t10.site_arrival_label, 'Attended At')
        self.assertTrue(t10.has_outage_tracking)
        self.assertIn('Warranty Claim', t10.final_status_choices)

        post_data = {
            'attended_by': [self.team_member.id],
            'work_request_no': 'WR-DSK-2026-001',
            'report_date': '2026-09-27',
            'eq_asset_tag_no': 'IT-DSK-042',
            'eq_equipment_type': 'Desktop',
            'outage_reported_at': '2026-09-27T09:00',
            'site_arrival_at': '2026-09-27T09:15',
            'restored_at': '2026-09-27T10:00',
            'total_downtime': '1h 00m',
            'reported_by': 'Finance Exec',
            'contact_no': '2105',
            'diag_status_1': 'Yes',
            'fault_selected': 'minor_issue',
            'action_taken_details': 'RAM cleaned and reseated',
            'faulty_item_disposal': 'N/A',
            'warranty_status': 'Under AMC',
            'verification_checks': ['System boots and runs normally'],
            'final_status': 'Restored and Closed',
        }
        resp = self.client.post(reverse('checklist_form', args=[t10.id]), data=post_data)
        self.assertEqual(resp.status_code, 302)

        sub = ChecklistSubmission.objects.get(work_request_no='WR-DSK-2026-001')
        self.assertEqual(sub.status, 'SUBMITTED')

        print_resp = self.client.get(reverse('checklist_print', args=[sub.id]))
        self.assertEqual(print_resp.status_code, 200)
        self.assertContains(print_resp, 'Fault Reported At')
        self.assertContains(print_resp, 'Attended At')

    def test_form_11_printer_troubleshooting_workflow(self):
        """Test Printer Troubleshooting Checklist (F/11)"""
        t11 = ChecklistTemplate.objects.create(
            doc_no='BIFPCL/IT/F/11',
            title='Printer Troubleshooting Report & Checklist',
            category='Printing & Peripheral Devices',
            revision='Rev: 00',
            retention_period='3 Years',
            equipment_fields_schema=[
                {'key': 'printer_id_tag', 'label': 'Printer ID / Tag No.', 'required': True},
                {'key': 'connection_type', 'label': 'Connection Type', 'options': ['USB', 'LAN', 'WiFi', 'Shared']},
            ],
            diagnostic_items_schema=[
                {'id': 1, 'text': 'Correct printer ID, location, and reported fault confirmed'},
            ],
            fault_options_schema=[
                {'key': 'consumable_issue', 'label': '2. Consumable issue', 'desc': 'Toner refilled'},
            ],
            verification_items_schema=['Test page printed successfully'],
        )
        self.assertEqual(t11.outage_reported_label, 'Fault Reported At')
        self.assertEqual(t11.site_arrival_label, 'Attended At')
        self.assertIn('Pending Consumable', t11.final_status_choices)

        post_data = {
            'attended_by': [self.team_member.id],
            'work_request_no': 'WR-PRN-2026-001',
            'report_date': '2026-09-27',
            'eq_printer_id_tag': 'PRN-ADM-02',
            'eq_connection_type': 'LAN',
            'diag_status_1': 'Yes',
            'fault_selected': 'consumable_issue',
            'action_taken_details': 'New black toner cartridge installed',
            'mat_desc[]': ['HP 58A Black Toner'],
            'mat_model[]': ['CF258A'],
            'mat_qty[]': ['1'],
            'mat_ref[]': ['STR-884'],
            'faulty_item_disposal': 'Store Return',
            'disposal_ref_no': 'RET-019',
            'warranty_status': 'Out of Warranty',
            'verification_checks': ['Test page printed successfully'],
            'final_status': 'Restored and Closed',
        }
        resp = self.client.post(reverse('checklist_form', args=[t11.id]), data=post_data)
        self.assertEqual(resp.status_code, 302)

        sub = ChecklistSubmission.objects.get(work_request_no='WR-PRN-2026-001')
        self.assertEqual(sub.status, 'SUBMITTED')

    def test_form_12_optical_fiber_cable_laying_and_jointing_workflow(self):
        """Test Form 12: Optical Fiber Cable Laying & Jointing Record (2-page physical form unified)"""
        t12 = ChecklistTemplate.objects.create(
            doc_no='BIFPCL/IT/F/12',
            title='Optical Fiber Cable Laying & Jointing Record',
            category='Fiber Optic & Transmission Infrastructure',
            revision='Rev: 00',
            retention_period='3 Years',
            equipment_fields_schema=[
                {'key': 'route_link_name', 'label': 'Route / Link Name', 'required': True},
                {'key': 'total_route_length', 'label': 'Total Route Length (m)', 'required': True},
                {'key': 'cable_type_core_count', 'label': 'Cable Type / Core Count', 'required': True},
                {'key': 'drum_batch_no', 'label': 'Drum / Batch No.', 'required': True},
                {'key': 'work_permit_no', 'label': 'Work Permit No.', 'required': False},
                {'key': 'height_work_ppe', 'label': 'Height Work / PPE', 'options': ['Height work', 'PPE used', 'Not applicable'], 'required': False},
            ],
            diagnostic_items_schema=[],
            fault_options_schema=[],
            materials_enabled=True,
            verification_items_schema=[],
        )
        self.assertTrue(t12.is_ofc)
        self.assertEqual(t12.default_job_id, 'BIFPCL/IT/OFC/2026/')
        self.assertEqual(t12.date_label, 'Record Date')
        self.assertFalse(t12.has_disposal)

        # 1. Technician visits form page
        form_get = self.client.get(reverse('checklist_form', args=[t12.id]))
        self.assertEqual(form_get.status_code, 200)
        self.assertContains(form_get, 'Cable Laying Details')
        self.assertContains(form_get, 'Joint Location Summary')
        self.assertContains(form_get, 'Jointing / Core Splice Schedule')
        self.assertContains(form_get, 'Testing and Acceptance')

        # 2. Technician submits OFC record (combining Page 1 and Page 2)
        post_data = {
            'attended_by': [self.team_member.id],
            'work_request_no': 'BIFPCL/IT/OFC/2026/014',
            'report_date': '2026-09-27',
            'eq_route_link_name': 'Switchyard Substation to Main Control Room',
            'eq_total_route_length': '1450',
            'eq_cable_type_core_count': '24-Core Armored Single Mode (G.652D)',
            'eq_drum_batch_no': 'DRUM-2026-OF-09',
            'eq_work_permit_no': 'WP/2026/0942',
            'eq_height_work_ppe': 'PPE used',

            # Cable Laying Details (Page 1)
            'ofc_cl_drum[]': ['DRUM-09', 'DRUM-09'],
            'ofc_cl_from[]': ['SWYD Pit 1', 'MH-03'],
            'ofc_cl_to[]': ['MH-03', 'MCR Trench'],
            'ofc_cl_path[]': ['Buried', 'Tray'],
            'ofc_cl_start[]': ['0', '750'],
            'ofc_cl_end[]': ['750', '1450'],
            'ofc_cl_laid[]': ['750', '700'],
            'ofc_cl_slack[]': ['15', '20'],
            'ofc_cl_remarks[]': ['HDPE Pipe laid', 'Tray clamped'],
            'ofc_total_cable_laid': '1450',
            'ofc_total_slack_reserve': '35',

            # Joint Location Summary (Page 1)
            'ofc_js_no[]': ['J-01'],
            'ofc_js_loc[]': ['MH-03 Switchyard Road'],
            'ofc_js_box[]': ['FJC-09'],
            'ofc_js_in[]': ['DRUM-09 / Pit 1'],
            'ofc_js_out[]': ['DRUM-09 / MCR'],
            'ofc_js_cores[]': ['24'],
            'ofc_js_date[]': ['2026-09-27'],
            'ofc_js_splicer[]': ['IT Fiber Team'],

            # Splice Schedule Header & 12 Cores (Page 1)
            'ofc_sch_joint_no': 'J-01',
            'ofc_sch_location': 'MH-03 Switchyard Road',
            'ofc_sch_closure_id': 'FJC-09',
            'ofc_sch_tray_no': 'Tray 01',
            'ofc_sp_in_cable[]': [f'C1-F{i+1}' for i in range(12)],
            'ofc_sp_in_tube[]': ['Blue'] * 12,
            'ofc_sp_in_core[]': [f'Core {i+1}' for i in range(12)],
            'ofc_sp_out_cable[]': [f'C2-F{i+1}' for i in range(12)],
            'ofc_sp_out_tube[]': ['Blue'] * 12,
            'ofc_sp_out_core[]': [f'Core {i+1}' for i in range(12)],
            'ofc_sp_loss[]': ['0.02'] * 12,
            'ofc_sp_remarks[]': ['Passed'] * 12,

            # Testing and Acceptance (5 rows: 4 on Page 1, 1 on Page 2)
            'ofc_ta_test[]': ['OTDR', 'OTDR', 'Power Meter', 'VFL', 'OTDR'],
            'ofc_ta_end_a[]': ['SWYD Substation', 'SWYD Substation', 'SWYD Substation', 'SWYD Substation', 'MCR'],
            'ofc_ta_end_b[]': ['MCR Rack 01', 'MCR Rack 01', 'MCR Rack 01', 'MCR Rack 01', 'SWYD Substation'],
            'ofc_ta_wave[]': ['1310 nm', '1550 nm', '1310 nm', '650 nm', '1550 nm'],
            'ofc_ta_loss[]': ['0.32 dB/km', '0.21 dB/km', '-18.4 dBm', 'Continuous Red', '0.22 dB/km'],
            'ofc_ta_result[]': ['Pass', 'Pass', 'Pass', 'Pass', 'Pass'],

            # Materials and Warranty (Page 2)
            'mat_desc[]': ['24-Core Dome Joint Closure', 'Fiber Splice Protection Sleeves 60mm', 'SC-LC Duplex Patch Cord 3M SM'],
            'mat_model[]': ['FJC-24P-DOME', 'SPS-60', 'SC-LC-SM-3M'],
            'mat_qty[]': ['1', '24', '2'],
            'mat_ref[]': ['SR-OFC-8821', 'SR-OFC-8821', 'SR-OFC-8822'],
            'warranty_status': 'Under Warranty',
            'vendor_po_ref': 'PO-2026-FIBER-01',

            # Remarks (Page 2)
            'ofc_general_remarks': 'Route fully backfilled with warning tape 300mm above duct. All 24 splices sealed inside IP68 closure.',
        }
        resp = self.client.post(reverse('checklist_form', args=[t12.id]), data=post_data)
        self.assertEqual(resp.status_code, 302)

        sub = ChecklistSubmission.objects.get(work_request_no='BIFPCL/IT/OFC/2026/014')
        self.assertEqual(sub.status, 'SUBMITTED')
        self.assertEqual(sub.custom_data['total_cable_laid'], '1450')
        self.assertEqual(len(sub.custom_data['cable_laying']), 2)
        self.assertEqual(sub.custom_data['splice_header']['closure_id'], 'FJC-09')
        self.assertEqual(len(sub.custom_data['splice_schedule']), 12)
        self.assertEqual(len(sub.custom_data['testing_acceptance']), 5)
        self.assertIn('IP68 closure', sub.custom_data['general_remarks'])

        # 3. Test Detail View
        detail_resp = self.client.get(reverse('checklist_detail', args=[sub.id]))
        self.assertEqual(detail_resp.status_code, 200)
        self.assertContains(detail_resp, 'Cable Laying Details')
        self.assertContains(detail_resp, 'DRUM-09')
        self.assertContains(detail_resp, 'FJC-09')
        self.assertContains(detail_resp, '1450')

        # 4. Test 2-Page Print View
        print_resp = self.client.get(reverse('checklist_print', args=[sub.id]))
        self.assertEqual(print_resp.status_code, 200)
        self.assertContains(print_resp, 'Page</strong> 1 of 2')
        self.assertContains(print_resp, 'Page</strong> 2 of 2')
        self.assertContains(print_resp, 'Optical Fiber Cable Laying &amp; Jointing Record')
        self.assertContains(print_resp, 'Cable Laying Details')
        self.assertContains(print_resp, 'Joint Location Summary')
        self.assertContains(print_resp, 'Jointing / Core Splice Schedule')
        self.assertContains(print_resp, 'Testing and Acceptance (Continuation)')
        self.assertContains(print_resp, 'Materials and Warranty')

        # 5. Supervisor Review & Forward
        self.client.login(username='sabbir', password='Password123!')
        rev_resp = self.client.post(reverse('supervisor_review', args=[sub.id]), data={
            'action': 'forward',
            'supervisor_remarks': 'OFC OTDR traces verified within standard limits.'
        })
        self.assertEqual(rev_resp.status_code, 302)
        sub.refresh_from_db()
        self.assertEqual(sub.status, 'FORWARDED')

        # 6. Manager Final Approval
        self.client.login(username='kasad', password='Password123!')
        app_resp = self.client.post(reverse('manager_approve', args=[sub.id]), data={
            'action': 'approve',
            'manager_remarks': 'Approved for commissioning and link activation.'
        })
        self.assertEqual(app_resp.status_code, 302)
        sub.refresh_from_db()
        self.assertEqual(sub.status, 'APPROVED')
        self.assertIsNotNone(sub.approved_at)

    def test_email_notifications_on_submit_and_forward(self):
        """
        Verify that:
        1. When attendee submits form, an email is sent to all 3 active Supervisors:
           - Sabbir (sabbir.supervisor@bifpcl.com)
           - Swarup (swarup.supervisor@bifpcl.com)
           - Ramjan (ramjan.supervisor@bifpcl.com)
        2. When supervisor reviews and forwards it, an email is sent to active Managers:
           - Assistant Manager Kasad (kasad.am@bifpcl.com)
           - Deputy Manager Tanvir (tanvir.dm@bifpcl.com)
        """
        mail.outbox = []

        # 1. Attendee submits checklist
        post_data = {
            'attended_by': [self.team_member.id],
            'work_request_no': 'WR-MAIL-TEST-01',
            'report_date': '2026-09-27',
            'eq_camera_id': 'CAM-SUB-01',
            'eq_location': 'Main Switchyard',
            'diag_status_1': 'Yes',
            'diag_remarks_1': 'All clear',
            'fault_selected': 'minor',
            'action_taken_details': 'Resolved loose patch cord.',
            'verification_checks': ['Camera online and live view stable'],
            'final_status': 'Restored and Closed',
        }
        submit_resp = self.client.post(reverse('checklist_form', args=[self.template.id]), data=post_data)
        self.assertEqual(submit_resp.status_code, 302)

        # Check that 1 email was dispatched containing all 3 supervisors in recipient list
        self.assertEqual(len(mail.outbox), 1)
        sup_email = mail.outbox[0]
        self.assertIn('sabbir.supervisor@bifpcl.com', sup_email.to)
        self.assertIn('swarup.supervisor@bifpcl.com', sup_email.to)
        self.assertIn('ramjan.supervisor@bifpcl.com', sup_email.to)
        self.assertIn('New Checklist Awaiting Review', sup_email.subject)
        self.assertIn('WR-MAIL-TEST-01', sup_email.body)
        self.assertIn('supervisor/review', sup_email.body)

        sub = ChecklistSubmission.objects.get(work_request_no='WR-MAIL-TEST-01')

        # 2. Supervisor reviews and forwards checklist (e.g., Sabbir)
        self.client.login(username='sabbir', password='Password123!')
        forward_resp = self.client.post(reverse('supervisor_review', args=[sub.id]), data={
            'action': 'forward',
            'supervisor_remarks': 'Checked configuration and verified online status.'
        })
        self.assertEqual(forward_resp.status_code, 302)

        # Check that 2nd email was dispatched containing both managers (Kasad and Tanvir)
        self.assertEqual(len(mail.outbox), 2)
        mgr_email = mail.outbox[1]
        self.assertIn('kasad.am@bifpcl.com', mgr_email.to)
        self.assertIn('tanvir.dm@bifpcl.com', mgr_email.to)
        self.assertIn('Checklist Forwarded for Final Approval', mgr_email.subject)
        self.assertIn(sub.tracking_no, mgr_email.subject)
        self.assertIn('Checked configuration and verified online status.', mgr_email.body)
        self.assertIn('manager/approve', mgr_email.body)

    def test_all_supervisors_and_managers_individual_actions(self):
        """
        Verify that all 3 supervisors (Sabbir, Swarup, Ramjan) and both managers
        (Assistant Manager Kasad, Deputy Manager Tanvir) can independently review and approve.
        """
        # Test Supervisor Swarup reviewing and forwarding
        sub1 = ChecklistSubmission.objects.create(
            template=self.template,
            work_request_no='WR-SWARUP-01',
            status='SUBMITTED'
        )
        sub1.attended_by.add(self.team_member)
        self.client.login(username='swarup', password='Password123!')
        resp1 = self.client.post(reverse('supervisor_review', args=[sub1.id]), data={
            'action': 'forward',
            'supervisor_remarks': 'Reviewed by Swarup Mohon'
        })
        self.assertEqual(resp1.status_code, 302)
        sub1.refresh_from_db()
        self.assertEqual(sub1.status, 'FORWARDED')
        self.assertEqual(sub1.supervised_by, self.supervisor_swarup)

        # Test Deputy Manager Tanvir reviewing and approving
        self.client.logout()
        self.client.login(username='tanvir', password='Password123!')
        resp2 = self.client.post(reverse('manager_approve', args=[sub1.id]), data={
            'action': 'approve',
            'manager_remarks': 'Approved by Deputy Manager Tanvir Islam'
        })
        self.assertEqual(resp2.status_code, 302)
        sub1.refresh_from_db()
        self.assertEqual(sub1.status, 'APPROVED')
        self.assertEqual(sub1.approved_by, self.deputy_manager)

        # Test Supervisor Ramjan reviewing and returning
        sub2 = ChecklistSubmission.objects.create(
            template=self.template,
            work_request_no='WR-RAMJAN-01',
            status='SUBMITTED'
        )
        sub2.attended_by.add(self.team_member)
        self.client.logout()
        self.client.login(username='ramjan', password='Password123!')
        resp3 = self.client.post(reverse('supervisor_review', args=[sub2.id]), data={
            'action': 'return',
            'supervisor_remarks': 'Returned by Ramjan Ali for verification'
        })
        self.assertEqual(resp3.status_code, 302)
        sub2.refresh_from_db()
        self.assertEqual(sub2.status, 'RETURNED')
        self.assertEqual(sub2.supervisor_remarks, 'Returned by Ramjan Ali for verification')

    def test_reports_only_accessible_by_manager(self):
        """
        Verify that the central Operations Reports & Audit Archive is exclusively
        accessible by Managers (AM / DM), and blocked for IT members and Supervisors.
        Also verify CSV report export functionality for Managers.
        """
        # 1. Unauthenticated user is redirected to login
        self.client.logout()
        resp_anon = self.client.get(reverse('audit_archive'))
        self.assertEqual(resp_anon.status_code, 302)
        self.assertTrue('/login/' in resp_anon.url)

        # 2. IT Team member cannot access reports archive
        self.client.login(username='alamin', password='Password123!')
        resp_it = self.client.get(reverse('audit_archive'))
        self.assertEqual(resp_it.status_code, 302)
        self.assertNotEqual(resp_it.url, reverse('audit_archive'))

        # 3. Supervisor cannot access reports archive
        self.client.logout()
        self.client.login(username='sabbir', password='Password123!')
        resp_sup = self.client.get(reverse('audit_archive'))
        self.assertEqual(resp_sup.status_code, 302)
        self.assertNotEqual(resp_sup.url, reverse('audit_archive'))

        # 4. Manager (Assistant Manager Kasad) CAN access reports archive
        self.client.logout()
        self.client.login(username='kasad', password='Password123!')
        resp_mgr = self.client.get(reverse('audit_archive'))
        self.assertEqual(resp_mgr.status_code, 200)
        self.assertContains(resp_mgr, 'Operations Reports')
        self.assertContains(resp_mgr, 'Manager Access Only')

        # 5. Manager can export CSV report
        resp_csv = self.client.get(reverse('audit_archive') + '?export=csv')
        self.assertEqual(resp_csv.status_code, 200)
        self.assertEqual(resp_csv['Content-Type'], 'text/csv')
        self.assertTrue('BIFPCL_IT_Operations_Report_' in resp_csv['Content-Disposition'])
        self.assertContains(resp_csv, 'Tracking Ref,Doc No,Checklist Title')


