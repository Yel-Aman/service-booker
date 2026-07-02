from django.shortcuts import redirect
from .models import City


def set_city(request):
    city_id = request.POST.get('city_id') or request.GET.get('city_id')
    if city_id:
        request.session['city_id'] = int(city_id)
        city = City.objects.get(pk=city_id)
        request.session['city_name'] = city.name_ru
    return redirect(request.META.get('HTTP_REFERER', '/'))


def get_current_city(request):
    city_id = request.session.get('city_id', 1)  # По умолчанию Атырау
    try:
        return City.objects.get(pk=city_id)
    except City.DoesNotExist:
        return City.objects.first()

def cities_context(request):
    return {'all_cities': City.objects.filter(is_active=True)}