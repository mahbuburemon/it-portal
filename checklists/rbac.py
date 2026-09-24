from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def is_supervisor(user):
    if not user.is_authenticated:
        return False
    return user.groups.filter(name='Supervisor').exists() or user.is_superuser


def is_manager(user):
    if not user.is_authenticated:
        return False
    return user.groups.filter(name='Manager').exists() or user.is_superuser


def supervisor_required(view_func):
    """Restricts access to Supervisors and Administrators."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Please log in to access the Supervisor Portal.")
            return redirect('login')
        if not is_supervisor(request.user) and not is_manager(request.user):
            messages.error(request, "Access denied: You must be a designated Supervisor to perform this action.")
            return redirect('main_dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def manager_required(view_func):
    """Restricts access to Assistant Manager, Deputy Manager, and Administrators."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Please log in to access the Management Approval Portal.")
            return redirect('login')
        if not is_manager(request.user):
            messages.error(request, "Access denied: This action requires Assistant Manager or Deputy Manager privileges.")
            return redirect('supervisor_dashboard' if is_supervisor(request.user) else 'main_dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
