# core/templatetags/auth_extras.py
from django import template
from django.contrib.auth.models import Group

register = template.Library()

@register.filter(name='has_group')
def has_group(user, group_name):
    """
    Checks if a user belongs to a specific group.
    Usage: {% if user|has_group:"Manager" %}
    """
    if user.is_authenticated:
        try:
            # Check efficiently if the group exists in the user's groups
            return user.groups.filter(name=group_name).exists()
        except Group.DoesNotExist:
            return False
    return False

# Optional: Alternative tag that takes multiple group names
# @register.filter(name='in_groups')
# def in_groups(user, group_names_str):
#     """ Checks if user is in any of the comma-separated group names """
#     if user.is_authenticated:
#         group_names = [name.strip() for name in group_names_str.split(',')]
#         return user.groups.filter(name__in=group_names).exists()
#     return False