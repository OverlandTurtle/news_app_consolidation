from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Publisher, Article


# Register your models here.
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Role", {"fields": ("role",)}),
        (
            "Reader subscriptions",
            {"fields": ("subscribed_publishers", "subscribed_journalists")},
        ),
    )

    list_display = ("username", "email", "role", "is_staff", "is_active")

    filter_horizontal = ("subscribed_publishers", "subscribed_journalists")


@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    list_display = ("name", "website", "created_at")
    search_fields = ("name",)
    filter_horizontal = ("editors", "journalists")


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "publisher", "journalist", "is_approved", "created_at")
    list_filter = ("is_approved", "publisher", "created_at")
    search_fields = ("title", "summary", "body", "journalist__username")
