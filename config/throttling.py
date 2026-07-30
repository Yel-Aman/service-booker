from django.core.cache import cache


def is_rate_limited(request, action, limit, window_seconds):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    client_ip = forwarded_for.split(',')[0].strip() or request.META.get(
        'REMOTE_ADDR',
        'unknown',
    )
    key = f'rate-limit:{action}:{client_ip}'
    if cache.add(key, 1, timeout=window_seconds):
        return False
    try:
        attempts = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window_seconds)
        return False
    return attempts > limit
