from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .models import is_admin


def admin_only(view_func):
    """Only staff users can open the page. Others are sent back to their dashboard."""

    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_admin(request.user):
            messages.error(request, 'Only administrators can open that page.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)

    return wrapper
