from django.utils import timezone

from .models import Notification


def globals(request):
    user = getattr(request, "user", None)
    ctx = {"today": timezone.localdate()}
    if user is not None and user.is_authenticated:
        ctx["unread_count"] = Notification.objects.filter(user=user, is_read=False).count()
        ctx["recent_notifications"] = Notification.objects.filter(user=user)[:5]
    return ctx
