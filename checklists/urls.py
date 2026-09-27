from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Public (No Login)
    path('', views.main_dashboard, name='main_dashboard'),
    path('form/<int:template_id>/', views.checklist_form, name='checklist_form'),
    path('edit/<int:submission_id>/', views.checklist_edit, name='checklist_edit'),
    path('success/<str:tracking_no>/', views.submission_success, name='submission_success'),
    path('view/<int:submission_id>/', views.checklist_detail, name='checklist_detail'),
    path('print/<int:submission_id>/', views.checklist_print, name='checklist_print'),

    # Authentication & Routing
    path('login/', auth_views.LoginView.as_view(template_name='checklists/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('role-redirect/', views.role_redirect, name='role_redirect'),

    # Stage 2: Supervisor Dashboard & Review
    path('supervisor/', views.supervisor_dashboard, name='supervisor_dashboard'),
    path('supervisor/review/<int:submission_id>/', views.supervisor_review, name='supervisor_review'),

    # Stage 3: Manager Dashboard & Approval
    path('manager/', views.manager_dashboard, name='manager_dashboard'),
    path('manager/approve/<int:submission_id>/', views.manager_approve, name='manager_approve'),

    # Historical Archive & Search
    path('archive/', views.audit_archive, name='audit_archive'),
]
