from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from news_app.models import Article


class Command(BaseCommand):
    help = "Create roles (groups) and assign permissions."

    def handle(self, *args, **options):
        readers_group, _ = Group.objects.get_or_create(name="Readers")
        editors_group, _ = Group.objects.get_or_create(name="Editors")
        journalists_group, _ = Group.objects.get_or_create(name="Journalists")

        article_ct = ContentType.objects.get_for_model(Article)

        def get_perm(codename: str) -> Permission:
            return Permission.objects.get(content_type=article_ct, codename=codename)

        # Reader: view only
        readers_group.permissions.set(
            [
                get_perm("view_article"),
            ]
        )

        # Editor: view, update, delete
        editors_group.permissions.set(
            [
                get_perm("view_article"),
                get_perm("change_article"),
                get_perm("delete_article"),
            ]
        )

        # Journalist: create, view, update, delete
        journalists_group.permissions.set(
            [
                get_perm("add_article"),
                get_perm("view_article"),
                get_perm("change_article"),
                get_perm("delete_article"),
            ]
        )

        self.stdout.write(self.style.SUCCESS("Groups + permissions are set up."))
