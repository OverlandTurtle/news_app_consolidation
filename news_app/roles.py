from django.contrib.auth.models import Group


def ensure_role_groups_exist():
    Group.objects.get_or_create(name="Readers")
    Group.objects.get_or_create(name="Editors")
    Group.objects.get_or_create(name="Journalists")
