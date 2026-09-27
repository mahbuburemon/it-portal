from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from checklists.models import TeamMember, ChecklistTemplate, ChecklistSubmission
from django.utils import timezone


class BIFPCLWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Groups
        self.sup_group = Group.objects.create(name='Supervisor')
        self.mgr_group = Group.objects.create(name='Manager')

        # Users
        self.supervisor = User.objects.create_user(
            username='sup1', password='Password123!', first_name='Rafiqul', last_name='Islam'
        )
        self.supervisor.groups.add(self.sup_group)

        self.manager = User.objects.create_user(
            username='mgr1', password='Password123!', first_name='Kazi', last_name='Rahman'
        )
        self.manager.groups.add(self.mgr_group)

        # Team Member
        self.team_member = TeamMember.objects.create(
            name='Md. Al-Amin Hossain',
            employee_id='IT-EMP-101',
            designation='Senior IT Executive',
            phone='+880 1711-000001'
        )

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
        """IT Team Members can access the dashboard and see checklists without login."""
        response = self.client.get(reverse('main_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'CCTV Troubleshooting Report')
        self.assertContains(response, 'BIFPCL/IT/F/01')



    def test_public_checklist_submission_without_login(self):
        """IT Team members can select multiple attending technicians and submit without login."""
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

        # Verify submission in database
        sub = ChecklistSubmission.objects.get(work_request_no='WR-999')
        self.assertEqual(sub.status, 'SUBMITTED')
        self.assertEqual(sub.attended_by.count(), 2)
        self.assertIn(self.team_member, sub.attended_by.all())
        self.assertIn(self.team_member2, sub.attended_by.all())
        self.assertEqual(sub.equipment_data['camera_id']['value'], 'CAM-GATE-01')
        self.assertIsNone(sub.supervised_by)
        self.assertIsNone(sub.approved_by)

    def test_rbac_security_boundaries(self):
        """Anonymous and unauthorized users are prevented from supervisor and manager views."""
        # Anonymous access blocked
        resp_sup = self.client.get(reverse('supervisor_dashboard'))
        self.assertEqual(resp_sup.status_code, 302)
        self.assertIn('/login/', resp_sup.url)

        resp_mgr = self.client.get(reverse('manager_dashboard'))
        self.assertEqual(resp_mgr.status_code, 302)
        self.assertIn('/login/', resp_mgr.url)

        # Supervisor cannot access Manager dashboard
        self.client.login(username='sup1', password='Password123!')
        resp_mgr_as_sup = self.client.get(reverse('manager_dashboard'))
        self.assertEqual(resp_mgr_as_sup.status_code, 302)
        self.assertEqual(resp_mgr_as_sup.url, reverse('supervisor_dashboard'))

        # Manager cannot access Supervisor dashboard
        self.client.logout()
        self.client.login(username='mgr1', password='Password123!')
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
        self.client.login(username='sup1', password='Password123!')
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
        self.client.login(username='mgr1', password='Password123!')
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
        self.assertContains(print_resp, 'Rafiqul Islam')
        self.assertContains(print_resp, 'Kazi Rahman')
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
        self.client.login(username='sup1', password='Password123!')
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

        # 5. Member accesses the edit form without login
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
        self.client.login(username='sup1', password='Password123!')
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
        self.client.login(username='mgr1', password='Password123!')
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



