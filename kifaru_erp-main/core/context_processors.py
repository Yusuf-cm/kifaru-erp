from .access import can_use_pos, is_manager


def access_flags(request):
    user = request.user
    return {
        "can_manage": is_manager(user),
        "can_use_pos": can_use_pos(user),
    }
