from django.urls import path
from . import api_views

app_name = "news_app_api"

urlpatterns = [
    path("me/feed/", api_views.my_feed, name="my_feed"),
    path(
        "articles/<int:article_id>/",
        api_views.article_detail_api,
        name="article_detail_api",
    ),
]
