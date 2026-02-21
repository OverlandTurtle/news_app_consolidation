from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Article, CustomUser
from .serializers import ArticleFeedSerializer


@api_view(["GET"])
def my_feed(request):
    """
    Reader only endpoint.
    Returns approved articles,
    filtered by the authenticated Reader's subscriptions:
    - subscribed publishers
    - subscribed journalists.
    """

    if request.user.role != CustomUser.ROLE_READER:
        return Response(
            {"ok": False, "error": "Only Readers can access this feed."},
            status=403,
        )

    # Get subscription IDs, safe even if empty
    publisher_ids = request.user.subscribed_publishers.values_list("id", flat=True)

    journalist_ids = request.user.subscribed_journalists.values_list("id", flat=True)

    # Build: approved AND, publisher in subs OR journalist in subs.
    # If both subscription lists are empty, return an empty list.
    articles_qs = Article.objects.filter(is_approved=True).order_by("-created_at")

    if publisher_ids or journalist_ids:
        articles_qs = articles_qs.filter(
            Q(publisher_id__in=publisher_ids) | Q(journalist_id__in=journalist_ids)
        ).distinct()

    else:
        articles_qs = articles_qs.none()

    serializer = ArticleFeedSerializer(articles_qs, many=True)

    return Response(
        {
            "ok": True,
            "count": len(serializer.data),
            "data": serializer.data,
        }
    )


@api_view(["GET"])
def article_detail_api(request, article_id):
    """
    GET /api/articles/<id>/

    Reader only endpoint.
    Returns a single approved article, only if it matches the authenticated
    Reader's subscriptions (publisher OR journalist).

    If not allowed, return 404.
    """

    if request.user.role != CustomUser.ROLE_READER:
        return Response(
            {"ok": False, "error": "Only Readers can access article details."},
            status=403,
        )

    publisher_ids = request.user.subscribed_publishers.values_list("id", flat=True)

    journalist_ids = request.user.subscribed_journalists.values_list("id", flat=True)

    # Only approved articles can be fetched via the API
    qs = Article.objects.filter(is_approved=True)

    # If no subscriptions, they can't access any detail
    if not publisher_ids and not journalist_ids:
        return Response({"ok": False, "error": "Not found."}, status=404)

    # Limit to the reader’s subscriptions (publisher OR journalist)
    qs = qs.filter(
        Q(publisher_id__in=publisher_ids) | Q(journalist_id__in=journalist_ids)
    ).distinct()

    # Fetch or 404
    article = get_object_or_404(qs, id=article_id)

    serializer = ArticleFeedSerializer(article)

    return Response({"ok": True, "data": serializer.data})
