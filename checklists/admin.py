from django.contrib import admin
from .models import TeamMember, ChecklistTemplate, ChecklistSubmission


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'employee_id', 'designation', 'phone', 'is_active')
    search_fields = ('name', 'employee_id', 'designation')
    list_filter = ('is_active', 'designation')


@admin.register(ChecklistTemplate)
class ChecklistTemplateAdmin(admin.ModelAdmin):
    list_display = ('doc_no', 'title', 'category', 'revision', 'is_active')
    search_fields = ('doc_no', 'title', 'category')
    list_filter = ('category', 'is_active')


@admin.register(ChecklistSubmission)
class ChecklistSubmissionAdmin(admin.ModelAdmin):
    list_display = ('tracking_no', 'template', 'get_attended_by', 'status', 'submitted_at', 'supervised_by', 'approved_by')
    list_filter = ('status', 'template__category', 'submitted_at')
    search_fields = ('tracking_no', 'work_request_no', 'attended_by__name')
    readonly_fields = ('tracking_no', 'submitted_at', 'created_at', 'updated_at')
    filter_horizontal = ('attended_by',)

    def get_attended_by(self, obj):
        return obj.attended_by_display
    get_attended_by.short_description = 'Attended By'

