from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from checklists.models import TeamMember, ChecklistTemplate
from django.utils import timezone


class Command(BaseCommand):
    help = 'Seeds initial BIFPCL data: RBAC groups, 5 user accounts, 14 IT team members, and 12 checklist templates.'

    def handle(self, *args, **options):
        self.stdout.write("--- Seeding Groups & Roles ---")
        sup_group, _ = Group.objects.get_or_create(name='Supervisor')
        mgr_group, _ = Group.objects.get_or_create(name='Manager')

        # 1. Create Superuser
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'first_name': 'IT System',
                'last_name': 'Administrator',
                'email': 'admin@bifpcl.com',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin.set_password('Admin@2026!')
            admin.save()
            self.stdout.write(self.style.SUCCESS("Created admin superuser (Admin@2026!)"))

        # 2. Create 3 Supervisors
        supervisors_data = [
            ('supervisor1', 'Md. Rafiqul', 'Islam', 'rafiqul.supervisor@bifpcl.com'),
            ('supervisor2', 'Tanvir', 'Ahmed', 'tanvir.supervisor@bifpcl.com'),
            ('supervisor3', 'Suman', 'Chakraborty', 'suman.supervisor@bifpcl.com'),
        ]
        for uname, fname, lname, email in supervisors_data:
            u, created = User.objects.get_or_create(
                username=uname,
                defaults={
                    'first_name': fname,
                    'last_name': lname,
                    'email': email,
                    'is_staff': True,
                }
            )
            u.set_password('Bifpcl@2026!')
            u.groups.add(sup_group)
            u.save()
            self.stdout.write(f"Synced Supervisor: {uname}")

        # 3. Create 2 Managers (1 Assistant Manager, 1 Deputy Manager)
        managers_data = [
            ('asst_manager', 'Engr. Kazi Mahfuzur', 'Rahman', 'kazi.am@bifpcl.com'),
            ('deputy_manager', 'Engr. Md. Tariqul', 'Hasan', 'tariqul.dm@bifpcl.com'),
        ]
        for uname, fname, lname, email in managers_data:
            u, created = User.objects.get_or_create(
                username=uname,
                defaults={
                    'first_name': fname,
                    'last_name': lname,
                    'email': email,
                    'is_staff': True,
                }
            )
            u.set_password('Bifpcl@2026!')
            u.groups.add(mgr_group)
            u.save()
            self.stdout.write(f"Synced Manager: {uname}")

        # 4. Create 14 IT Team Members
        self.stdout.write("\n--- Seeding 14 IT Team Members (Attended By) ---")
        team_members_data = [
            ('Md. Al-Amin Hossain', 'IT-EMP-101', 'Senior IT Executive', '+880 1711-000001'),
            ('Mohammad Shamim Reza', 'IT-EMP-102', 'Assistant IT Engineer', '+880 1711-000002'),
            ('Farhana Yasmin', 'IT-EMP-103', 'Network Support Engineer', '+880 1711-000003'),
            ('Shahriar Kabir', 'IT-EMP-104', 'System Administrator', '+880 1711-000004'),
            ('A.H.M. Kamrul Hasan', 'IT-EMP-105', 'IT Support Specialist', '+880 1711-000005'),
            ('Nasir Uddin Mahmud', 'IT-EMP-106', 'Hardware & Network Technician', '+880 1711-000006'),
            ('Rezaul Karim', 'IT-EMP-107', 'CCTV & Surveillance Specialist', '+880 1711-000007'),
            ('Sajid Bin Alam', 'IT-EMP-108', 'Data Center Associate', '+880 1711-000008'),
            ('Mehedi Hasan Rony', 'IT-EMP-109', 'Field IT Support Engineer', '+880 1711-000009'),
            ('Tanzim Ahmed', 'IT-EMP-110', 'Access Control & Telecom Tech', '+880 1711-000010'),
            ('Anisur Rahman', 'IT-EMP-111', 'Desktop & Peripherals Technician', '+880 1711-000011'),
            ('Zahidul Islam', 'IT-EMP-112', 'Power & UPS Systems Technician', '+880 1711-000012'),
            ('Sharmin Akter', 'IT-EMP-113', 'Junior IT Officer', '+880 1711-000013'),
            ('Imran Hossain', 'IT-EMP-114', 'Network Operations Technician', '+880 1711-000014'),
        ]

        for name, emp_id, desig, phone in team_members_data:
            tm, created = TeamMember.objects.get_or_create(
                employee_id=emp_id,
                defaults={
                    'name': name,
                    'designation': desig,
                    'phone': phone,
                    'is_active': True,
                }
            )
            self.stdout.write(f"Synced Team Member: {name} ({emp_id})")

        # 5. Create 12 Checklist Templates
        self.stdout.write("\n--- Seeding 12 Checklist Templates ---")
        
        # Form 1: Exact CCTV Troubleshooting Report & Checklist (from user's document)
        cctv_template, _ = ChecklistTemplate.objects.get_or_create(
            doc_no='BIFPCL/IT/F/01',
            defaults={
                'title': 'CCTV Troubleshooting Report & Checklist',
                'category': 'Surveillance & Physical Security',
                'revision': 'Rev: 00',
                'retention_period': '3 Years',
                'icon': 'camera-video',
                'description': 'Maintenance, diagnostic and fault restoration checklist for plant and boundary CCTV cameras.',
                'equipment_fields_schema': [
                    {'key': 'camera_id_name', 'label': 'Camera ID / Name', 'placeholder': 'e.g. CAM-GATE-01 / PTZ-COAL-YARD', 'required': True},
                    {'key': 'location', 'label': 'Location', 'placeholder': 'e.g. Main Gate Substation / Switchyard', 'required': True},
                ],
                'diagnostic_items_schema': [
                    {'id': 1, 'text': 'Correct camera ID and location confirmed'},
                    {'id': 2, 'text': 'Camera physically inspected for damage or tampering'},
                    {'id': 3, 'text': 'Power plug, adapter, DC connector, or PoE checked'},
                    {'id': 4, 'text': 'Network cable and RJ45 connectors checked'},
                    {'id': 5, 'text': 'Fiber cable and media converter checked, if applicable'},
                    {'id': 6, 'text': 'Switch-port and link/activity indicators checked'},
                    {'id': 7, 'text': 'Lens / dome cleanliness, alignment, and focus checked'},
                ],
                'fault_options_schema': [
                    {
                        'key': 'minor_issue',
                        'label': '1. Minor issue corrected',
                        'desc': 'Loose power plug, network cable, fiber patch cord, or connector.'
                    },
                    {
                        'key': 'camera_operational_image',
                        'label': '2. Camera operational; image issue corrected',
                        'desc': 'Alignment, focus, blurriness, dirty lens or dome, or obstruction.'
                    },
                    {
                        'key': 'power_issue',
                        'label': '3. Power issue',
                        'desc': 'Camera unavailable due to missing or faulty power supply.'
                    },
                    {
                        'key': 'replacement_required',
                        'label': '4. Replacement required',
                        'desc': 'Network or fiber cable, media converter, adapter, PoE device, camera, or other item.'
                    }
                ],
                'materials_enabled': True,
                'verification_items_schema': [
                    'Camera online and live view stable',
                    'Field of view and focus acceptable',
                    'Recording and playback verified',
                    'Cables, enclosure, and mounting secured',
                    'Control room confirmation received',
                    'Work area left safe and clean',
                ]
            }
        )
        self.stdout.write(f"Synced Form: {cctv_template.doc_no} - {cctv_template.title}")

        # Clean up any other templates if present
        deleted_count, _ = ChecklistTemplate.objects.exclude(doc_no='BIFPCL/IT/F/01').delete()
        if deleted_count:
            self.stdout.write(f"Removed {deleted_count} non-CCTV checklist template(s).")

        self.stdout.write(self.style.SUCCESS("\n[SUCCESS] Successfully seeded all groups, 5 users, 14 team members, and CCTV Troubleshooting Checklist!"))

