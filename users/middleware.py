from django.utils import timezone

from .models import UserDailyActivity


class DailyActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            UserDailyActivity.objects.get_or_create(
                user=request.user,
                date=timezone.localdate(),
            )
        return self.get_response(request)
