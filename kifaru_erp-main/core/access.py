from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseForbidden


MANAGER_GROUP = "Manager"
CASHIER_GROUP = "Cashier"


def is_manager(user):
    return (
        user.is_authenticated
        and (
            user.is_superuser
            or user.groups.filter(name=MANAGER_GROUP).exists()
        )
    )


def can_use_pos(user):
    return (
        user.is_authenticated
        and (
            user.is_superuser
            or user.groups.filter(name__in=[MANAGER_GROUP, CASHIER_GROUP]).exists()
        )
    )


def role_required(check):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not check(request.user):
                return HttpResponseForbidden("You do not have permission to access this area.")
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator


manager_required = role_required(is_manager)
pos_required = role_required(can_use_pos)
