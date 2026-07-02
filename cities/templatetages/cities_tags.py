from django import template
from cities.models import City

register = template.Library()

@register.simple_tag
def get_cities():
    return City.objects.filter(is_active=True)