from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings


class CustomUser(AbstractUser):
    """
    Custom user model with role field.

    - Role selects which Group the user is placed into:
      Readers / Editors / Journalists.
    - Subscriptions only for Readers. Django ManyToMany fields cannot be None,
      so we enforce "empty" vs "used".

    """

    ROLE_READER = "reader"
    ROLE_EDITOR = "editor"
    ROLE_JOURNALIST = "journalist"

    ROLE_CHOICES = [
        (ROLE_READER, "Reader"),
        (ROLE_EDITOR, "Editor"),
        (ROLE_JOURNALIST, "Journalist"),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_READER,
    )

    # Reader fields (subscriptions)
    subscribed_publishers = models.ManyToManyField(
        "Publisher",
        blank=True,
        related_name="subscribed_readers",
    )

    subscribed_journalists = models.ManyToManyField(
        "CustomUser",
        blank=True,
        related_name="subscribed_readers_to_journalists",
        limit_choices_to={"role": ROLE_JOURNALIST},
    )

    def __str__(self) -> str:
        return self.username


class Publisher(models.Model):
    """
    A news publisher.
    - A publisher can have multiple editors and journalists.
    """

    name = models.CharField(max_length=120, unique=True)
    website = models.URLField(blank=True)

    editors = models.ManyToManyField(
        "CustomUser",
        blank=True,
        related_name="publishers_as_editor",
        limit_choices_to={"role": CustomUser.ROLE_EDITOR},
    )

    journalists = models.ManyToManyField(
        "CustomUser",
        blank=True,
        related_name="publishers_as_journalist",
        limit_choices_to={"role": CustomUser.ROLE_JOURNALIST},
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Article(models.Model):
    """
    An article written by a journalist.
    - Must indicate whether the article has been approved by an editor or not.
    """

    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles",
    )

    journalist = models.ForeignKey(
        "CustomUser",
        on_delete=models.CASCADE,
        related_name="independent_articles",
        limit_choices_to={"role": CustomUser.ROLE_JOURNALIST},
    )

    title = models.CharField(max_length=200)
    summary = models.CharField(max_length=300, blank=True)
    body = models.TextField()

    is_approved = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class Newsletter(models.Model):
    publisher = models.ForeignKey(
        "Publisher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="newsletters",
    )

    journalist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="newsletters",
        limit_choices_to={"role": CustomUser.ROLE_JOURNALIST},
    )

    title = models.CharField(max_length=200)
    body = models.TextField()

    is_approved = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
