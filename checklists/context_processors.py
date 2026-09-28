from .rbac import is_supervisor, is_manager, is_it_member


def user_roles(request):
    """
    Exposes role-based booleans to all templates for conditional navigation
    and role segregation.
    """
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        return {
            'user_is_supervisor': is_supervisor(user),
            'user_is_manager': is_manager(user),
            'user_is_it_member': is_it_member(user),
            'user_team_profile': getattr(user, 'team_profile', None),
        }
    return {
        'user_is_supervisor': False,
        'user_is_manager': False,
        'user_is_it_member': False,
        'user_team_profile': None,
    }
