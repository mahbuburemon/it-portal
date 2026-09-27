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
        cctv_template, _ = ChecklistTemplate.objects.update_or_create(
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

        # Form 2: New CCTV Installation Report & Checklist (Exact match to official physical form)
        installation_template, _ = ChecklistTemplate.objects.update_or_create(
            doc_no='BIFPCL/IT/F/02',
            defaults={
                'title': 'New CCTV Installation Report & Checklist',
                'category': 'Surveillance & Physical Security',
                'revision': 'Rev: 00',
                'retention_period': '3 Years',
                'icon': 'camera-video-fill',
                'description': 'Physical installation, mounting, cabling, VMS configuration, and commissioning checklist for new CCTV cameras.',
                'equipment_fields_schema': [
                    {'key': 'camera_id_1', 'label': 'Camera ID / Name 1', 'placeholder': 'e.g. CAM-GATE-02 / PTZ-COAL-02', 'required': True},
                    {'key': 'location_1', 'label': 'Location', 'placeholder': 'e.g. Sentry Gate North', 'required': True},
                    {'key': 'camera_id_2', 'label': 'Camera ID / Name 2', 'placeholder': 'e.g. CAM-GATE-03 (Optional dual unit)', 'required': False},
                    {'key': 'location_2', 'label': 'Location', 'placeholder': 'e.g. Sentry Gate South', 'required': False},
                    {'key': 'camera_model', 'label': 'Camera Model', 'placeholder': 'e.g. Hikvision DS-2CD2T87G2-L', 'required': True},
                    {'key': 'serial_no', 'label': 'Serial No.', 'placeholder': 'e.g. SN-8923478912', 'required': True},
                    {'key': 'work_permit_no', 'label': 'Work Permit No.', 'placeholder': 'e.g. WP/2026/0412', 'required': False},
                    {'key': 'height_work_ppe', 'label': 'Height Work / PPE', 'options': ['Height work', 'PPE used', 'Not applicable'], 'required': False},
                ],
                'diagnostic_items_schema': [
                    {'id': 1, 'text': 'Proper alignment'},
                    {'id': 2, 'text': 'Proper focus'},
                    {'id': 3, 'text': 'Night vision check'},
                    {'id': 4, 'text': 'Cable tags fixed at both ends'},
                    {'id': 5, 'text': 'JB / Rack / Cabinet closed'},
                    {'id': 6, 'text': 'Work area left safe and clean'},
                ],
                'fault_options_schema': [],
                'materials_enabled': True,
                'verification_items_schema': [
                    'Both VMS servers configured, if applicable',
                    'Camera online and live view stable',
                    'Recording and playback verified',
                    'NTP setup and date-time confirmation',
                    'Camera name and location updated in records',
                    'Field of view and focus acceptable',
                    'Control room confirmation received',
                    'Work area left safe and clean',
                ]
            }
        )
        self.stdout.write(f"Synced Form: {installation_template.doc_no} - {installation_template.title}")

        # Form 3: CCTV Replacement Report & Checklist (Exact match to official physical form)
        cctv_rep_template, _ = ChecklistTemplate.objects.update_or_create(
            doc_no='BIFPCL/IT/F/03',
            defaults={
                'title': 'CCTV Replacement Report & Checklist',
                'category': 'Surveillance & Physical Security',
                'revision': 'Rev: 00',
                'retention_period': '3 Years',
                'icon': 'arrow-repeat',
                'description': 'Field replacement, de-commissioning, new camera mounting, VMS re-linking and commissioning checklist.',
                'equipment_fields_schema': [
                    {'key': 'camera_id_1', 'label': 'Camera ID / Name 1', 'placeholder': 'e.g. CAM-GATE-01', 'required': True},
                    {'key': 'location_1', 'label': 'Location', 'placeholder': 'e.g. Main Sentry Gate', 'required': True},
                    {'key': 'camera_id_2', 'label': 'Camera ID / Name 2', 'placeholder': 'e.g. CAM-GATE-02 (if dual)', 'required': False},
                    {'key': 'location_2', 'label': 'Location', 'placeholder': 'e.g. Vehicle Bay', 'required': False},
                    {'key': 'damaged_camera_model', 'label': 'Damaged Camera Model', 'placeholder': 'e.g. DS-2CD2T47G1-L', 'required': True},
                    {'key': 'replacing_camera_model', 'label': 'Replacing Camera Model', 'placeholder': 'e.g. DS-2CD2T87G2-L', 'required': True},
                    {'key': 'damaged_camera_serial', 'label': 'Damaged Camera Serial', 'placeholder': 'e.g. SN-OLD-7821', 'required': True},
                    {'key': 'replacing_camera_serial', 'label': 'Replacing Camera Serial', 'placeholder': 'e.g. SN-NEW-9912', 'required': True},
                    {'key': 'work_permit_no', 'label': 'Work Permit No.', 'placeholder': 'e.g. WP/2026/0512', 'required': False},
                    {'key': 'height_work_ppe', 'label': 'Height Work / PPE', 'options': ['Height work', 'PPE used', 'Not applicable'], 'required': False},
                ],
                'diagnostic_items_schema': [
                    {'id': 1, 'text': 'Proper alignment'},
                    {'id': 2, 'text': 'Proper focus'},
                    {'id': 3, 'text': 'Night vision check'},
                    {'id': 4, 'text': 'Cable tags fixed at both ends'},
                    {'id': 5, 'text': 'JB / Rack / Cabinet closed'},
                    {'id': 6, 'text': 'Work area left safe and clean'},
                ],
                'fault_options_schema': [],
                'materials_enabled': True,
                'verification_items_schema': [
                    'Both VMS servers configured, if applicable',
                    'NTP setup and date-time confirmation',
                    'Camera online and live view stable',
                    'Field of view and focus acceptable',
                    'Recording and playback verified',
                    'Camera name updated in VMS',
                    'Control room confirmation received',
                    'Work area left safe and clean',
                ]
            }
        )
        self.stdout.write(f"Synced Form: {cctv_rep_template.doc_no} - {cctv_rep_template.title}")

        # Form 4: AP Troubleshooting Report & Checklist (Exact match to official physical form)
        ap_trouble_template, _ = ChecklistTemplate.objects.update_or_create(
            doc_no='BIFPCL/IT/F/04',
            defaults={
                'title': 'AP Troubleshooting Report & Checklist',
                'category': 'Network & Wireless Infrastructure',
                'revision': 'Rev: 00',
                'retention_period': '3 Years',
                'icon': 'wifi',
                'description': 'Diagnostic, fault isolation, wireless coverage restoration, and corrective maintenance checklist for plant WiFi Access Points.',
                'equipment_fields_schema': [
                    {'key': 'ap_id_name', 'label': 'AP ID / Name', 'placeholder': 'e.g. AP-ADMIN-01', 'required': True},
                    {'key': 'location', 'label': 'Location', 'placeholder': 'e.g. Admin Building 2nd Floor', 'required': True},
                    {'key': 'ap_model', 'label': 'AP Model', 'placeholder': 'e.g. Cisco Catalyst 9120AX', 'required': True},
                    {'key': 'serial_no', 'label': 'Serial No.', 'placeholder': 'e.g. FOC24190XXX', 'required': True},
                    {'key': 'controller_port', 'label': 'Controller & Port', 'placeholder': 'e.g. WLC-01 / Gi1/0/24', 'required': False},
                    {'key': 'ssid_vlan', 'label': 'SSID / VLAN', 'placeholder': 'e.g. BIFPCL_CORP / VLAN 120', 'required': False},
                ],
                'diagnostic_items_schema': [
                    {'id': 1, 'text': 'Correct AP ID and location confirmed'},
                    {'id': 2, 'text': 'AP physically inspected for damage, tampering, or loose mounting'},
                    {'id': 3, 'text': 'AP LED / status indicator and PoE source (switch port or injector) checked'},
                    {'id': 4, 'text': 'Network cable, patch cord, RJ45 connectors, and switch-port link / VLAN checked'},
                    {'id': 5, 'text': 'AP reachable and online in controller / management console'},
                    {'id': 6, 'text': 'SSID broadcast, association, and authentication tested'},
                    {'id': 7, 'text': 'Signal strength (RSSI) and channel interference checked'},
                    {'id': 8, 'text': 'Client IP (DHCP), gateway reachability, and internet speed tested'},
                ],
                'fault_options_schema': [
                    {
                        'key': 'minor_issue',
                        'label': '1. Minor issue corrected',
                        'desc': 'Loose power or network cable, patch cord, connector, or PoE injector reseated.'
                    },
                    {
                        'key': 'config_issue',
                        'label': '2. Configuration issue corrected',
                        'desc': 'SSID, VLAN, channel, transmit power, IP/DHCP, or firmware setting.'
                    },
                    {
                        'key': 'power_issue',
                        'label': '3. Power issue',
                        'desc': 'AP unavailable due to missing or faulty PoE port, injector, or power supply.'
                    },
                    {
                        'key': 'coverage_issue',
                        'label': '4. Coverage or interference issue',
                        'desc': 'Repositioning, channel change, or additional AP required.'
                    },
                    {
                        'key': 'replacement_required',
                        'label': '5. Replacement required',
                        'desc': 'AP, PoE injector, patch cord, network cable, or other item.'
                    }
                ],
                'materials_enabled': True,
                'verification_items_schema': [
                    'AP online in controller',
                    'SSID broadcasting and clients associating',
                    'Signal strength acceptable in coverage area',
                    'Internet speed / throughput verified',
                    'Telephone link checked, if applicable',
                    'Cables, mounting, and enclosure secured',
                    'User confirmation received',
                    'Work area left safe and clean',
                ]
            }
        )
        self.stdout.write(f"Synced Form: {ap_trouble_template.doc_no} - {ap_trouble_template.title}")

        # Form 5: New AP Installation Report & Checklist (Exact match to official physical form)
        ap_install_template, _ = ChecklistTemplate.objects.update_or_create(
            doc_no='BIFPCL/IT/F/05',
            defaults={
                'title': 'New AP Installation Report & Checklist',
                'category': 'Network & Wireless Infrastructure',
                'revision': 'Rev: 00',
                'retention_period': '3 Years',
                'icon': 'router',
                'description': 'Mounting, cabling, PoE provisioning, WLC adoption, SSID broadcasting, and commissioning checklist for new WiFi Access Points.',
                'equipment_fields_schema': [
                    {'key': 'ap_id_name', 'label': 'AP ID / Name', 'placeholder': 'e.g. AP-PLANT-04', 'required': True},
                    {'key': 'location', 'label': 'Location', 'placeholder': 'e.g. Turbine Hall Bay 2', 'required': True},
                    {'key': 'ap_model', 'label': 'AP Model', 'placeholder': 'e.g. Cisco Catalyst 9120AXI', 'required': True},
                    {'key': 'serial_no', 'label': 'Serial No.', 'placeholder': 'e.g. FOC25100YYY', 'required': True},
                    {'key': 'controller_port', 'label': 'Controller & Port', 'placeholder': 'e.g. WLC-01 / Te1/0/12', 'required': False},
                    {'key': 'ssid_vlan', 'label': 'SSID / VLAN', 'placeholder': 'e.g. BIFPCL_PLANT / VLAN 140', 'required': False},
                    {'key': 'mounting_type', 'label': 'Mounting Type', 'options': ['Ceiling', 'Wall', 'Pole', 'Other'], 'required': False},
                    {'key': 'power_source', 'label': 'Power Source', 'options': ['PoE Switch', 'Injector', 'Adapter'], 'required': False},
                    {'key': 'work_permit_no', 'label': 'Work Permit No.', 'placeholder': 'e.g. WP/2026/0681', 'required': False},
                    {'key': 'height_work_ppe', 'label': 'Height Work / PPE', 'options': ['Height work', 'PPE used', 'Not applicable'], 'required': False},
                ],
                'diagnostic_items_schema': [
                    {'id': 1, 'text': 'AP mounted securely with correct orientation'},
                    {'id': 2, 'text': 'Cable laid, dressed, and routed properly'},
                    {'id': 3, 'text': 'Cable tags fixed at both ends'},
                    {'id': 4, 'text': 'PoE switch port or injector connected and rated'},
                    {'id': 5, 'text': 'Switch port configured (VLAN / PoE) and labeled'},
                    {'id': 6, 'text': 'Telephone link check, if applicable'},
                    {'id': 7, 'text': 'AP pairing / adoption to controller confirmed'},
                    {'id': 8, 'text': 'JB / Rack / Cabinet closed'},
                    {'id': 9, 'text': 'Work area left safe and clean'},
                ],
                'fault_options_schema': [],
                'materials_enabled': True,
                'verification_items_schema': [
                    'AP online in controller',
                    'SSID broadcast and authentication verified',
                    'IP address / DHCP confirmed',
                    'NTP setup and date-time confirmation',
                    'Firmware version checked and updated',
                    'AP name and location updated in records',
                    'WiFi signal OK in coverage area',
                    'WiFi speed / throughput OK',
                    'Control room / user confirmation received',
                    'Work area left safe and clean',
                ]
            }
        )
        self.stdout.write(f"Synced Form: {ap_install_template.doc_no} - {ap_install_template.title}")

        # Form 6: AP Replacement Report & Checklist (Exact match to official physical form)
        ap_rep_template, _ = ChecklistTemplate.objects.update_or_create(
            doc_no='BIFPCL/IT/F/06',
            defaults={
                'title': 'AP Replacement Report & Checklist',
                'category': 'Network & Wireless Infrastructure',
                'revision': 'Rev: 00',
                'retention_period': '3 Years',
                'icon': 'arrow-repeat',
                'description': 'Field replacement, de-commissioning, new AP mounting, WLC re-adoption and commissioning checklist.',
                'equipment_fields_schema': [
                    {'key': 'ap_id_name', 'label': 'AP ID / Name', 'placeholder': 'e.g. AP-ADMIN-01', 'required': True},
                    {'key': 'location', 'label': 'Location', 'placeholder': 'e.g. Admin Building 2nd Floor', 'required': True},
                    {'key': 'damaged_ap_model', 'label': 'Damaged AP Model', 'placeholder': 'e.g. Cisco AP 2802I', 'required': True},
                    {'key': 'replacing_ap_model', 'label': 'Replacing AP Model', 'placeholder': 'e.g. Cisco Catalyst 9120AXI', 'required': True},
                    {'key': 'damaged_ap_serial', 'label': 'Damaged AP Serial', 'placeholder': 'e.g. FOC22010XXX', 'required': True},
                    {'key': 'replacing_ap_serial', 'label': 'Replacing AP Serial', 'placeholder': 'e.g. FOC25100YYY', 'required': True},
                    {'key': 'work_permit_no', 'label': 'Work Permit No.', 'placeholder': 'e.g. WP/2026/0721', 'required': False},
                    {'key': 'height_work_ppe', 'label': 'Height Work / PPE', 'options': ['Height work', 'PPE used', 'Not applicable'], 'required': False},
                ],
                'diagnostic_items_schema': [
                    {'id': 1, 'text': 'Proper AP mounting'},
                    {'id': 2, 'text': 'Cable dressed and routed properly'},
                    {'id': 3, 'text': 'Cable tags fixed at both ends'},
                    {'id': 4, 'text': 'Telephone link check, if applicable'},
                    {'id': 5, 'text': 'AP pairing confirmed'},
                    {'id': 6, 'text': 'Work area left safe and clean'},
                ],
                'fault_options_schema': [],
                'materials_enabled': True,
                'verification_items_schema': [
                    'WiFi signal OK',
                    'WiFi speed OK',
                    'AP online in controller',
                    'SSID broadcast and authentication verified',
                    'IP address / DHCP confirmed',
                    'AP name and location updated in records',
                    'User confirmation received',
                    'Work area left safe and clean',
                ]
            }
        )
        self.stdout.write(f"Synced Form: {ap_rep_template.doc_no} - {ap_rep_template.title}")

        # Form 7: Telephone Troubleshooting Report & Checklist (Exact match to official physical form)
        tel_trouble_template, _ = ChecklistTemplate.objects.update_or_create(
            doc_no='BIFPCL/IT/F/07',
            defaults={
                'title': 'Telephone Troubleshooting Report & Checklist',
                'category': 'Telecommunications & EPABX',
                'revision': 'Rev: 00',
                'retention_period': '3 Years',
                'icon': 'telephone',
                'description': 'Diagnostic, cable fault rectification, EPABX port configuration and extension restoration checklist for plant telephones.',
                'equipment_fields_schema': [
                    {'key': 'extension_no', 'label': 'Extension No.', 'placeholder': 'e.g. 2104', 'required': True},
                    {'key': 'location_user', 'label': 'Location / User', 'placeholder': 'e.g. Admin Room 102 / Accounts', 'required': True},
                    {'key': 'phone_type', 'label': 'Phone Type', 'options': ['Analog', 'IP', 'DECT', 'Hotline'], 'required': True},
                    {'key': 'phone_model_serial', 'label': 'Phone Model / Serial', 'placeholder': 'e.g. Panasonic KX-TS500 / SN-4921', 'required': False},
                    {'key': 'epabx_gateway_port', 'label': 'EPABX / Gateway Port', 'placeholder': 'e.g. Card 02 / Port 14', 'required': False},
                    {'key': 'mdf_krone_pair', 'label': 'MDF / Krone & Pair', 'placeholder': 'e.g. MDF-A / Block 03 / Pair 08', 'required': False},
                ],
                'diagnostic_items_schema': [
                    {'id': 1, 'text': 'Correct extension number and location confirmed'},
                    {'id': 2, 'text': 'Fault confirmed with user (no dial tone, no ring, one-way audio, noise, cannot dial)'},
                    {'id': 3, 'text': 'Telephone instrument inspected for physical damage'},
                    {'id': 4, 'text': 'Handset, handset cord, and line cord checked'},
                    {'id': 5, 'text': 'Power adapter or PoE checked, for IP phone'},
                    {'id': 6, 'text': 'Telephone cable, RJ11/RJ45 connector, and wall socket checked'},
                    {'id': 7, 'text': 'MDF / krone tag block and jumper checked; line tested with test phone'},
                    {'id': 8, 'text': 'EPABX port, card status, and extension programming checked'},
                    {'id': 9, 'text': 'Dial tone, incoming call, outgoing call, and voice quality tested'},
                ],
                'fault_options_schema': [
                    {
                        'key': 'minor_issue',
                        'label': '1. Minor issue corrected',
                        'desc': 'Loose handset cord, line cord, connector, or wall socket.'
                    },
                    {
                        'key': 'line_jumper_issue',
                        'label': '2. Line or jumper issue corrected',
                        'desc': 'MDF, krone tag block, jumper, or cable pair changed.'
                    },
                    {
                        'key': 'epabx_config_issue',
                        'label': '3. EPABX configuration issue corrected',
                        'desc': 'Extension programming, port, class of service, or registration.'
                    },
                    {
                        'key': 'power_issue',
                        'label': '4. Power issue',
                        'desc': 'IP phone unavailable due to missing or faulty PoE or power adapter.'
                    },
                    {
                        'key': 'replacement_required',
                        'label': '5. Replacement required',
                        'desc': 'Telephone instrument, handset, cord, line cable, or other item.'
                    }
                ],
                'materials_enabled': True,
                'verification_items_schema': [
                    'Dial tone available',
                    'Outgoing call tested',
                    'Incoming call and ringing tested',
                    'Voice quality (two-way audio) acceptable',
                    'Extension number and display verified',
                    'Cables, socket, and tag block secured',
                    'User confirmation received',
                    'Work area left safe and clean',
                ]
            }
        )
        self.stdout.write(f"Synced Form: {tel_trouble_template.doc_no} - {tel_trouble_template.title}")

        # Form 8: New Telephone Installation Report & Checklist (Exact match to official physical form)
        tel_install_template, _ = ChecklistTemplate.objects.update_or_create(
            doc_no='BIFPCL/IT/F/08',
            defaults={
                'title': 'New Telephone Installation Report & Checklist',
                'category': 'Telecommunications & EPABX',
                'revision': 'Rev: 00',
                'retention_period': '3 Years',
                'icon': 'telephone-plus',
                'description': 'Cabling, termination, EPABX programming, class of service configuration, and commissioning checklist for new telephones.',
                'equipment_fields_schema': [
                    {'key': 'extension_no', 'label': 'Extension No.', 'placeholder': 'e.g. 2150', 'required': True},
                    {'key': 'location_user', 'label': 'Location / User', 'placeholder': 'e.g. Service Building Bay 3', 'required': True},
                    {'key': 'phone_type', 'label': 'Phone Type', 'options': ['Analog', 'IP', 'DECT', 'Hotline'], 'required': True},
                    {'key': 'phone_model', 'label': 'Phone Model', 'placeholder': 'e.g. Grandstream GXP1625', 'required': True},
                    {'key': 'serial_no_mac', 'label': 'Serial No. / MAC', 'placeholder': 'e.g. 00:0B:82:XX:XX:XX', 'required': True},
                    {'key': 'epabx_gateway_port', 'label': 'EPABX / Gateway Port', 'placeholder': 'e.g. Switch-02 / Fa0/18', 'required': False},
                    {'key': 'mdf_krone_pair', 'label': 'MDF / Krone & Pair', 'placeholder': 'e.g. MDF-B / Krone 02 / Pair 04', 'required': False},
                    {'key': 'cable_type_length', 'label': 'Cable Type / Length', 'placeholder': 'e.g. 2-Pair UTP / 45M', 'required': False},
                    {'key': 'work_permit_no', 'label': 'Work Permit No.', 'placeholder': 'e.g. WP/2026/0890', 'required': False},
                    {'key': 'height_work_ppe', 'label': 'Height Work / PPE', 'options': ['Height work', 'PPE used', 'Not applicable'], 'required': False},
                ],
                'diagnostic_items_schema': [
                    {'id': 1, 'text': 'Cable laid, dressed, and routed properly'},
                    {'id': 2, 'text': 'Telephone socket / faceplate fixed and labeled'},
                    {'id': 3, 'text': 'MDF / krone termination and jumper completed'},
                    {'id': 4, 'text': 'Cable tags fixed at both ends'},
                    {'id': 5, 'text': 'EPABX port allotted and extension programmed'},
                    {'id': 6, 'text': 'Class of service / call restriction configured as approved'},
                    {'id': 7, 'text': 'Power (PoE or adapter) connected, for IP phone'},
                    {'id': 8, 'text': 'Instrument placed or mounted and cords connected'},
                    {'id': 9, 'text': 'JB / Rack / Cabinet closed'},
                ],
                'fault_options_schema': [],
                'materials_enabled': True,
                'verification_items_schema': [
                    'Dial tone available',
                    'Outgoing call tested',
                    'Incoming call and ringing tested',
                    'Voice quality (two-way audio) acceptable',
                    'Extension number and display verified',
                    'Speed dial / hotline configured, if applicable',
                    'Telephone directory / extension list updated',
                    'User handover and briefing completed',
                    'Control room confirmation received',
                    'Work area left safe and clean',
                ]
            }
        )
        self.stdout.write(f"Synced Form: {tel_install_template.doc_no} - {tel_install_template.title}")

        # Form 9: Telephone Replacement Report & Checklist (Exact match to official physical form)
        tel_rep_template, _ = ChecklistTemplate.objects.update_or_create(
            doc_no='BIFPCL/IT/F/09',
            defaults={
                'title': 'Telephone Replacement Report & Checklist',
                'category': 'Telecommunications & EPABX',
                'revision': 'Rev: 00',
                'retention_period': '3 Years',
                'icon': 'telephone-forward',
                'description': 'Field replacement, de-commissioning, new instrument installation, EPABX re-linking and commissioning checklist.',
                'equipment_fields_schema': [
                    {'key': 'extension_no', 'label': 'Extension No.', 'placeholder': 'e.g. 2104', 'required': True},
                    {'key': 'location_user', 'label': 'Location / User', 'placeholder': 'e.g. Accounts Department Desk 4', 'required': True},
                    {'key': 'phone_type', 'label': 'Phone Type', 'options': ['Analog', 'IP', 'DECT', 'Hotline'], 'required': True},
                    {'key': 'epabx_gateway_port', 'label': 'EPABX / Gateway Port', 'placeholder': 'e.g. Card 01 / Port 08', 'required': False},
                    {'key': 'damaged_phone_model', 'label': 'Damaged Phone Model', 'placeholder': 'e.g. KX-TS500', 'required': True},
                    {'key': 'replacing_phone_model', 'label': 'Replacing Phone Model', 'placeholder': 'e.g. KX-TS880', 'required': True},
                    {'key': 'damaged_phone_serial', 'label': 'Damaged Phone Serial', 'placeholder': 'e.g. SN-OLD-3312', 'required': True},
                    {'key': 'replacing_phone_serial', 'label': 'Replacing Phone Serial', 'placeholder': 'e.g. SN-NEW-7741', 'required': True},
                ],
                'diagnostic_items_schema': [
                    {'id': 1, 'text': 'Damaged instrument removed and defect recorded'},
                    {'id': 2, 'text': 'Replacement instrument placed or mounted properly'},
                    {'id': 3, 'text': 'Handset, handset cord, and line cord connected'},
                    {'id': 4, 'text': 'Telephone cable, connector, and wall socket checked'},
                    {'id': 5, 'text': 'MDF / krone termination and jumper checked'},
                    {'id': 6, 'text': 'Power (PoE or adapter) connected, for IP phone'},
                    {'id': 7, 'text': 'Cable tags and instrument label fixed'},
                    {'id': 8, 'text': 'Work area left safe and clean'},
                ],
                'fault_options_schema': [],
                'materials_enabled': True,
                'verification_items_schema': [
                    'Dial tone available',
                    'Outgoing call tested',
                    'Incoming call and ringing tested',
                    'Voice quality (two-way audio) acceptable',
                    'Extension number and display verified',
                    'MAC / registration updated in EPABX, for IP phone',
                    'Speed dial / hotline restored, if applicable',
                    'Telephone directory record updated',
                    'User confirmation received',
                    'Work area left safe and clean',
                ]
            }
        )
        self.stdout.write(f"Synced Form: {tel_rep_template.doc_no} - {tel_rep_template.title}")

        # Form 10: Desktop / Laptop Troubleshooting Report & Checklist (Exact match to official physical form)
        pc_trouble_template, _ = ChecklistTemplate.objects.update_or_create(
            doc_no='BIFPCL/IT/F/10',
            defaults={
                'title': 'Desktop / Laptop Troubleshooting Report & Checklist',
                'category': 'End-User Computing & Workstations',
                'revision': 'Rev: 00',
                'retention_period': '3 Years',
                'icon': 'laptop',
                'description': 'Diagnostic, hardware/software fault isolation, OS/antivirus recovery, and restoration checklist for desktops and laptops.',
                'equipment_fields_schema': [
                    {'key': 'asset_tag_no', 'label': 'Asset / Tag No.', 'placeholder': 'e.g. IT-DSK-042', 'required': True},
                    {'key': 'user_dept', 'label': 'User / Dept.', 'placeholder': 'e.g. Accounts / Finance', 'required': True},
                    {'key': 'equipment_type', 'label': 'Equipment Type', 'options': ['Desktop', 'Laptop', 'AIO', 'Other'], 'required': True},
                    {'key': 'location', 'label': 'Location', 'placeholder': 'e.g. Admin Building 1st Floor', 'required': True},
                    {'key': 'make_model', 'label': 'Make & Model', 'placeholder': 'e.g. Dell OptiPlex 7090', 'required': True},
                    {'key': 'serial_no', 'label': 'Serial No.', 'placeholder': 'e.g. CN-038291-ABCD', 'required': True},
                ],
                'diagnostic_items_schema': [
                    {'id': 1, 'text': 'Fault reported by user confirmed and reproduced'},
                    {'id': 2, 'text': 'User data backup taken or data safety confirmed before work'},
                    {'id': 3, 'text': 'Power supply, adapter, battery, power cable, and peripheral connections checked'},
                    {'id': 4, 'text': 'POST / beep code observed; RAM, SSD/HDD, and add-on cards reseated and tested'},
                    {'id': 5, 'text': 'Disk health (SMART), temperature, cooling fan, and internal cleaning checked'},
                    {'id': 6, 'text': 'BIOS/UEFI settings, boot order, and firmware version checked'},
                    {'id': 7, 'text': 'Operating system boot, drivers, updates, and antivirus status checked'},
                ],
                'fault_options_schema': [
                    {
                        'key': 'minor_issue',
                        'label': '1. Minor issue corrected',
                        'desc': 'Loose cable, connector, peripheral, or component reseated.'
                    },
                    {
                        'key': 'software_issue',
                        'label': '2. Software issue corrected',
                        'desc': 'Operating system, driver, update, user profile, or application setting.'
                    },
                    {
                        'key': 'malware_security_issue',
                        'label': '3. Malware or security issue corrected',
                        'desc': 'Scan, cleanup, or security policy applied.'
                    },
                    {
                        'key': 'hardware_fault',
                        'label': '4. Hardware fault',
                        'desc': 'Component faulty; repair or replacement of part required.'
                    },
                    {
                        'key': 'beyond_economic_repair',
                        'label': '5. Beyond economic repair or warranty',
                        'desc': 'Referred for vendor support, warranty claim, or condemnation.'
                    }
                ],
                'materials_enabled': True,
                'verification_items_schema': [
                    'System boots and runs normally',
                    'All peripherals working',
                    'User data intact and accessible',
                    'Network and domain login verified',
                    'Required applications working and antivirus updated',
                    'Asset / service record updated',
                    'User confirmation received',
                    'Work area left safe and clean',
                ]
            }
        )
        self.stdout.write(f"Synced Form: {pc_trouble_template.doc_no} - {pc_trouble_template.title}")

        # Form 11: Printer Troubleshooting Report & Checklist (Exact match to official physical form)
        printer_trouble_template, _ = ChecklistTemplate.objects.update_or_create(
            doc_no='BIFPCL/IT/F/11',
            defaults={
                'title': 'Printer Troubleshooting Report & Checklist',
                'category': 'Printing & Peripheral Devices',
                'revision': 'Rev: 00',
                'retention_period': '3 Years',
                'icon': 'printer',
                'description': 'Diagnostic, paper jam, toner/cartridge replacement, driver/spooler configuration, and hardware repair checklist for plant printers.',
                'equipment_fields_schema': [
                    {'key': 'printer_id_tag', 'label': 'Printer ID / Tag No.', 'placeholder': 'e.g. PRN-ADM-02', 'required': True},
                    {'key': 'location_dept', 'label': 'Location / Dept.', 'placeholder': 'e.g. HR Department Room 204', 'required': True},
                    {'key': 'make_model', 'label': 'Make & Model', 'placeholder': 'e.g. HP LaserJet Pro M404dn', 'required': True},
                    {'key': 'serial_no', 'label': 'Serial No.', 'placeholder': 'e.g. VNB3K08912', 'required': True},
                    {'key': 'connection_type', 'label': 'Connection Type', 'options': ['USB', 'LAN', 'WiFi', 'Shared'], 'required': True},
                    {'key': 'ip_hostname', 'label': 'IP Address / Hostname', 'placeholder': 'e.g. 192.168.10.85 / prn-adm-02', 'required': False},
                ],
                'diagnostic_items_schema': [
                    {'id': 1, 'text': 'Correct printer ID, location, and reported fault confirmed'},
                    {'id': 2, 'text': 'Power supply, power cable, switch, and USB / network cable checked'},
                    {'id': 3, 'text': 'Display panel error code or message noted'},
                    {'id': 4, 'text': 'Paper tray, paper path, and jam cleared'},
                    {'id': 5, 'text': 'Toner / cartridge / drum level and seating checked'},
                    {'id': 6, 'text': 'Rollers, ADF, fuser, and internal cleaning checked'},
                    {'id': 7, 'text': 'Self-test / configuration page printed and page count recorded'},
                    {'id': 8, 'text': 'IP address, port, network connectivity (ping), and print queue checked'},
                ],
                'fault_options_schema': [
                    {
                        'key': 'minor_issue',
                        'label': '1. Minor issue corrected',
                        'desc': 'Paper jam cleared, loose cable, tray, or cartridge reseated.'
                    },
                    {
                        'key': 'consumable_issue',
                        'label': '2. Consumable issue',
                        'desc': 'Toner, cartridge, or drum replaced or refilled.'
                    },
                    {
                        'key': 'config_issue',
                        'label': '3. Configuration issue corrected',
                        'desc': 'Driver, print queue, spooler, IP address, or sharing setting.'
                    },
                    {
                        'key': 'hardware_fault',
                        'label': '4. Hardware fault',
                        'desc': 'Roller, ADF, fuser, formatter, or other part requires repair or replacement.'
                    },
                    {
                        'key': 'vendor_support',
                        'label': '5. Vendor support required',
                        'desc': 'Warranty claim or vendor service call raised.'
                    }
                ],
                'materials_enabled': True,
                'verification_items_schema': [
                    'Test page printed successfully',
                    'Print quality acceptable',
                    'Scan and photocopy verified, if applicable',
                    'Network printing from user PC verified',
                    'Paper trays refilled and closed',
                    'Toner / cartridge and page count record updated',
                    'User confirmation received',
                    'Work area left safe and clean',
                ]
            }
        )
        self.stdout.write(f"Synced Form: {printer_trouble_template.doc_no} - {printer_trouble_template.title}")

        # Form 12: Optical Fiber Cable Laying & Jointing Record (Exact match to official physical form)
        ofc_record_template, _ = ChecklistTemplate.objects.update_or_create(
            doc_no='BIFPCL/IT/F/12',
            defaults={
                'title': 'Optical Fiber Cable Laying & Jointing Record',
                'category': 'Fiber Optic & Transmission Infrastructure',
                'revision': 'Rev: 00',
                'retention_period': '3 Years',
                'icon': 'diagram-3',
                'description': 'Cable laying details, drum records, joint location summary, 12-core splice schedule, OTDR/power meter acceptance testing, and commissioning record.',
                'equipment_fields_schema': [
                    {'key': 'route_link_name', 'label': 'Route / Link Name', 'placeholder': 'e.g. Switchyard Substation to Main Control Room', 'required': True},
                    {'key': 'total_route_length', 'label': 'Total Route Length (m)', 'placeholder': 'e.g. 1450', 'required': True},
                    {'key': 'cable_type_core_count', 'label': 'Cable Type / Core Count', 'placeholder': 'e.g. 24-Core Armored Single Mode (G.652D)', 'required': True},
                    {'key': 'drum_batch_no', 'label': 'Drum / Batch No.', 'placeholder': 'e.g. DRUM-2026-OF-09', 'required': True},
                    {'key': 'work_permit_no', 'label': 'Work Permit No.', 'placeholder': 'e.g. WP/2026/0942', 'required': False},
                    {'key': 'height_work_ppe', 'label': 'Height Work / PPE', 'options': ['Height work', 'PPE used', 'Not applicable'], 'required': False},
                ],
                'diagnostic_items_schema': [],
                'fault_options_schema': [],
                'materials_enabled': True,
                'verification_items_schema': []
            }
        )
        self.stdout.write(f"Synced Form: {ofc_record_template.doc_no} - {ofc_record_template.title}")

        # Clean up any non-standard templates
        deleted_count, _ = ChecklistTemplate.objects.exclude(doc_no__in=[
            'BIFPCL/IT/F/01', 'BIFPCL/IT/F/02', 'BIFPCL/IT/F/03',
            'BIFPCL/IT/F/04', 'BIFPCL/IT/F/05', 'BIFPCL/IT/F/06',
            'BIFPCL/IT/F/07', 'BIFPCL/IT/F/08', 'BIFPCL/IT/F/09',
            'BIFPCL/IT/F/10', 'BIFPCL/IT/F/11', 'BIFPCL/IT/F/12'
        ]).delete()
        if deleted_count:
            self.stdout.write(f"Removed {deleted_count} non-standard checklist template(s).")

        self.stdout.write(self.style.SUCCESS("\n[SUCCESS] Successfully seeded all groups, 5 users, 14 team members, and all 12 BIFPCL Checklists (F/01 to F/12)!"))

