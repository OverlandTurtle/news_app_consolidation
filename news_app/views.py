import os
import requests

from django.conf import settings
from django.core.mail import send_mail
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group
from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.http import require_http_methods
from .models import Article, Publisher, CustomUser, Newsletter
from django.db import models
from .forms import CustomUserCreationForm, ArticleForm, NewsletterForm
from django.utils.http import url_has_allowed_host_and_scheme


def home(request):
    # Simple landing page
    return render(request, "news_app/home.html")


def user_is_reader(user):
    """
    Role check.
    """
    return user.is_authenticated and getattr(
        user, "role", None) == CustomUser.ROLE_READER


def editor_can_manage_publisher_item(editor_user, publisher):
    """
    Returns True if editor_user is
    allowed to manage content for this publisher.
    - If publisher is independent: any editor allowed
    - If publisher exists: editor must be assigned to it
    """
    if publisher is None:
        return True

    return publisher.editors.filter(id=editor_user.id).exists()


@require_http_methods(["GET", "POST"])
def register_view(request):
    # If already logged in, don't allow registering again
    if request.user.is_authenticated:
        return redirect("news_app:dashboard")

    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)

        if form.is_valid():
            user = form.save()

            # Pick the correct role-group name based on the user's chosen role
            if user.role == CustomUser.ROLE_READER:
                group_name = "Readers"
            elif user.role == CustomUser.ROLE_EDITOR:
                group_name = "Editors"
            else:
                group_name = "Journalists"

            # Group should already exist via setup_roles,
            # but get_or_create keeps it safe
            group, _created = Group.objects.get_or_create(name=group_name)

            # User should only be in one role group
            user.groups.clear()
            user.groups.add(group)

            messages.success(
                request, "Account created successfully. Please log in."
            )

            return redirect("news_app:login")

        messages.error(request, "Please fix the errors below.")
    else:
        form = CustomUserCreationForm()

    return render(request, "news_app/auth/register.html", {"form": form})


@require_http_methods(["GET", "POST"])
def login_view(request):
    # If already logged in, don't allow logging in again
    if request.user.is_authenticated:
        return redirect("news_app:dashboard")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)

        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")

            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, "Logged in successfully.")
                return redirect("news_app:dashboard")

        messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()

    return render(request, "news_app/auth/login.html", {"form": form})


@login_required
def logout_view(request):
    # Log out the user and return home
    logout(request)
    messages.success(request, "Logged out successfully.")

    return redirect("news_app:home")


@login_required
def dashboard(request):
    return render(request, "news_app/dashboard.html")


def article_list(request):
    """
    Reader list page.
    Only show approved articles.
    """
    articles = Article.objects.filter(is_approved=True).order_by("-created_at")

    return render(
        request, "news_app/articles/article_list.html", {"articles": articles}
    )


def article_detail(request, article_id):
    """
    Reader detail page.
    Only allow access to approved articles (if not approved, 404).
    """
    article = get_object_or_404(Article, id=article_id, is_approved=True)

    return render(
        request, "news_app/articles/article_detail.html", {"article": article}
    )


def publisher_list(request):
    """
    Reader list of all publishers.
    """
    publishers = Publisher.objects.all().order_by("name")

    return render(
        request,
        "news_app/publishers/publisher_list.html",
        {"publishers": publishers},
    )


def journalist_list(request):
    """
    Reader list of all journalist users.
    Filter CustomUser by role to only show journalists.
    """
    journalists = CustomUser.objects.filter(
        role=CustomUser.ROLE_JOURNALIST).order_by("username")

    return render(
        request,
        "news_app/journalists/journalist_list.html",
        {"journalists": journalists},
    )


@login_required
@require_http_methods(["POST"])
def publisher_subscribe(request, publisher_id):
    # Only Readers can subscribe.
    if not user_is_reader(request.user):
        messages.error(request, "Only Readers can subscribe to publishers.")

        return redirect("news_app:publisher_list")

    publisher = get_object_or_404(Publisher, id=publisher_id)

    # Prevent duplicates.
    if publisher in request.user.subscribed_publishers.all():
        messages.info(request, "You are already subscribed to that publisher.")

        return redirect("news_app:publisher_list")

    request.user.subscribed_publishers.add(publisher)
    messages.success(request, f"Subscribed to {publisher.name}.")
    return redirect("news_app:publisher_list")


@login_required
@require_http_methods(["POST"])
def publisher_unsubscribe(request, publisher_id):
    if not user_is_reader(request.user):
        messages.error(
            request, "Only Readers can unsubscribe from publishers."
        )

        return redirect("news_app:publisher_list")

    publisher = get_object_or_404(Publisher, id=publisher_id)

    if publisher not in request.user.subscribed_publishers.all():
        messages.info(request, "You are not subscribed to that publisher.")

        return redirect("news_app:publisher_list")

    request.user.subscribed_publishers.remove(publisher)
    messages.success(request, f"Unsubscribed from {publisher.name}.")
    return redirect("news_app:publisher_list")


@login_required
@require_http_methods(["POST"])
def journalist_subscribe(request, journalist_id):
    if not user_is_reader(request.user):
        messages.error(request, "Only Readers can subscribe to journalists.")

        return redirect("news_app:journalist_list")

    journalist = get_object_or_404(
        CustomUser, id=journalist_id, role=CustomUser.ROLE_JOURNALIST
    )

    if journalist in request.user.subscribed_journalists.all():
        messages.info(
            request, "You are already subscribed to that journalist."
        )

        return redirect("news_app:journalist_list")

    request.user.subscribed_journalists.add(journalist)
    messages.success(request, f"Subscribed to {journalist.username}.")
    return redirect("news_app:journalist_list")


@login_required
@require_http_methods(["POST"])
def journalist_unsubscribe(request, journalist_id):
    if not user_is_reader(request.user):
        messages.error(
            request, "Only Readers can unsubscribe from journalists."
        )

        return redirect("news_app:journalist_list")

    journalist = get_object_or_404(
        CustomUser, id=journalist_id, role=CustomUser.ROLE_JOURNALIST
    )

    if journalist not in request.user.subscribed_journalists.all():
        messages.info(request, "You are not subscribed to that journalist.")

        return redirect("news_app:journalist_list")

    request.user.subscribed_journalists.remove(journalist)
    messages.success(request, f"Unsubscribed from {journalist.username}.")
    return redirect("news_app:journalist_list")


@login_required
@require_http_methods(["GET", "POST"])
def publisher_create(request):
    """
    Editor only.
    Allows editors to add a new Publisher from the normal UI (not admin).
    """

    if request.user.role != CustomUser.ROLE_EDITOR:
        messages.error(request, "Only editors can create publishers.")
        return redirect("news_app:dashboard")

    form_data = {
        "name": "",
        "website": "",
    }

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        website = (request.POST.get("website") or "").strip()

        form_data["name"] = name
        form_data["website"] = website

        # Basic validation
        if len(name) < 2:
            messages.error(request, "Publisher name must be at least 2 characters.")
            return render(
                request,
                "news_app/publishers/publisher_form.html",
                {"form_data": form_data},
            )

        # Unique check
        if Publisher.objects.filter(name__iexact=name).exists():
            messages.error(request, "That publisher already exists.")
            return render(
                request,
                "news_app/publishers/publisher_form.html",
                {"form_data": form_data},
            )

        publisher = Publisher.objects.create(
            name=name,
            website=website,
        )

        # Default assign current editor to this publisher
        publisher.editors.add(request.user)

        messages.success(request, f"Publisher created: {publisher.name}")

        next_url = request.GET.get("next")
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
        ):
            return redirect(next_url)

        return redirect("news_app:publisher_list")

    return render(
        request,
        "news_app/publishers/publisher_form.html",
        {"form_data": form_data},
    )


@login_required
def my_articles(request):
    """
    Journalist only.
    Shows the logged-in journalist's own articles, approved or not.
    """
    if request.user.role != CustomUser.ROLE_JOURNALIST:
        messages.error(request, "Only journalists can access My Articles.")

        return redirect("news_app:dashboard")

    articles = Article.objects.filter(
        journalist=request.user).order_by("-created_at")

    return render(
        request,
        "news_app/journalists/my_articles.html",
        {"articles": articles},
    )


@login_required
@require_http_methods(["GET", "POST"])
def article_create(request):
    """
    Journalist only.
    Articles created here are always drafts (is_approved=False).
    """
    if request.user.role != CustomUser.ROLE_JOURNALIST:
        messages.error(request, "Only journalists can create articles.")

        return redirect("news_app:dashboard")

    if request.method == "POST":
        form = ArticleForm(request.POST)

        if form.is_valid():
            article = form.save(commit=False)

            article.journalist = request.user
            article.is_approved = False

            article.save()
            messages.success(
                request, "Article draft created. It is not approved yet."
            )

            return redirect("news_app:my_articles")

        messages.error(request, "Please fix the errors below.")
    else:
        form = ArticleForm()

    return render(
        request, "news_app/journalists/article_form.html", {"form": form}
    )


@login_required
@require_http_methods(["GET", "POST"])
def article_edit(request, article_id):
    """
    Journalist only.
    Only allow editing on your own articles.
    If approved, editing is blocked.
    """
    if request.user.role != CustomUser.ROLE_JOURNALIST:
        messages.error(request, "Only journalists can edit their articles.")
        return redirect("news_app:dashboard")

    article = get_object_or_404(
        Article, id=article_id, journalist=request.user
    )

    if article.is_approved:
        messages.error(
            request, "This article is already approved and cannot be edited."
        )

        return redirect("news_app:my_articles")

    if request.method == "POST":
        form = ArticleForm(request.POST, instance=article)

        if form.is_valid():
            updated_article = form.save(commit=False)
            updated_article.journalist = request.user
            updated_article.is_approved = False  # false until editor approves.
            updated_article.save()

            messages.success(request, "Article updated.")
            return redirect("news_app:my_articles")

        messages.error(request, "Please fix the errors below.")
    else:
        form = ArticleForm(instance=article)

    return render(
        request,
        "news_app/journalists/article_form.html",
        {"form": form, "article": article, "is_edit": True},
    )


@login_required
@require_http_methods(["POST"])
def article_delete(request, article_id):
    """
    Journalist only.
    Only allow deleting own articles.
    If approved, deleting is blocked.
    """
    if request.user.role != CustomUser.ROLE_JOURNALIST:
        messages.error(request, "Only journalists can delete articles.")

        return redirect("news_app:dashboard")

    article = get_object_or_404(
        Article, id=article_id, journalist=request.user
    )

    if article.is_approved:
        messages.error(
            request, "This article is already approved and cannot be deleted."
        )

        return redirect("news_app:my_articles")

    article_title = article.title
    article.delete()
    messages.success(request, f"Deleted article: {article_title}")

    return redirect("news_app:my_articles")


@login_required
def editor_pending_articles(request):
    """
    Editor only.
    Shows all articles that are not approved yet.
    """
    if request.user.role != CustomUser.ROLE_EDITOR:
        messages.error(
            request, "Only editors can access the editor dashboard."
        )

        return redirect("news_app:dashboard")

    pending_articles = Article.objects.filter(
        is_approved=False).order_by("-created_at")
    # Editors can approve:
    # independent articles (publisher is NULL)
    # publisher-linked articles, only if they are assigned to that publisher
    allowed_publisher_ids = request.user.publishers_as_editor.values_list(
        "id", flat=True)

    pending_articles = pending_articles.filter(
        models.Q(publisher__isnull=True)
        | models.Q(publisher_id__in=allowed_publisher_ids)
    ).distinct()

    return render(
        request,
        "news_app/editors/pending_articles.html",
        {"pending_articles": pending_articles},
    )


@login_required
@require_http_methods(["POST"])
def editor_approve_article(request, article_id):
    """
    Editor only.
    Approves an article (is_approved=True) then:
    - emails subscribers (publisher + journalist subscriptions)
    - posts to X
    No signals.

    Even if email/X fails, the approval still succeeds.
    """
    if request.user.role != CustomUser.ROLE_EDITOR:
        messages.error(request, "Only editors can approve articles.")
        return redirect("news_app:dashboard")

    article = get_object_or_404(Article, id=article_id)

    # If this is linked to a publisher, only assigned editors may approve it.
    if article.publisher is not None:
        is_assigned = article.publisher.editors.filter(id=request.user.id).exists()
        if not is_assigned:
            messages.error(request, "You cannot approve articles for this publisher.")
            return redirect("news_app:editor_pending_articles")

    if article.is_approved:
        messages.info(request, "That article is already approved.")
        return redirect("news_app:editor_pending_articles")

    # Approve first
    article.is_approved = True
    article.save()

    # Pull all subscribers: publisher subs + journalist subs
    subscriber_qs = CustomUser.objects.filter(role=CustomUser.ROLE_READER)

    publisher_subs = subscriber_qs.none()
    if article.publisher:
        publisher_subs = subscriber_qs.filter(
            subscribed_publishers=article.publisher)

    journalist_subs = subscriber_qs.filter(
        subscribed_journalists=article.journalist)

    subscribers = (publisher_subs | journalist_subs).distinct()

    email_list = []
    for user in subscribers:
        if user.email:
            email_list.append(user.email)

    # Email (send if possible)
    email_sent = False

    if email_list:
        subject = f"New article approved: {article.title}"
        body = (
            f"{article.title}\n\n"
            f"{article.summary}\n\n"
            f"Read it here: http://127.0.0.1:8000/articles/{article.id}/\n"
        )

        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=email_list,
                fail_silently=False,
            )
            email_sent = True
        except Exception:
            # Approval still succeeds, we’ll just show a warning below.
            pass

    # X post (try, but approval still succeeds if this fails)

    x_posted = False

    try:
        bearer_token = os.getenv("X_BEARER_TOKEN")
        x_post_url = os.getenv("X_POST_URL")  # set later

        if bearer_token and x_post_url:
            tweet_text = (
                f"{article.title} - http://127.0.0.1:8000/articles/{article.id}/"
            )

            headers = {
                "Authorization": f"Bearer {bearer_token}",
                "Content-Type": "application/json",
            }
            payload = {"text": tweet_text}

            resp = requests.post(
                x_post_url,
                headers=headers,
                json=payload,
                timeout=10,
            )
            resp.raise_for_status()
            x_posted = True

    except Exception:
        # Approval still succeeds, just show warning/info below.
        pass

    messages.success(request, f"Approved: {article.title}")

    if email_list:
        if email_sent:
            messages.success(request, f"Emailed {len(email_list)} subscriber(s).")
        else:
            messages.warning(request, "Article approved, but email failed.")
    else:
        messages.info(request, "Article approved. No subscriber emails to send.")

    if x_posted:
        messages.success(request, "Posted to X successfully.")
    else:
        if os.getenv("X_BEARER_TOKEN") and os.getenv("X_POST_URL"):
            messages.warning(request, "Article approved, but X posting failed.")
        else:
            messages.info(request, "X posting not configured yet (skipped).")

    return redirect("news_app:editor_pending_articles")


@login_required
def editor_pending_newsletters(request):
    """
    Editor only.
    Shows all newsletters that are not approved yet.
    """
    if request.user.role != CustomUser.ROLE_EDITOR:
        messages.error(request, "Only editors can access the editor dashboard.")
        return redirect("news_app:dashboard")

    pending_newsletters = Newsletter.objects.filter(
        is_approved=False
    ).order_by("-created_at")

    allowed_publisher_ids = request.user.publishers_as_editor.values_list(
        "id", flat=True
    )

    pending_newsletters = pending_newsletters.filter(
        models.Q(publisher__isnull=True)
        | models.Q(publisher_id__in=allowed_publisher_ids)
    ).distinct()

    return render(
        request,
        "news_app/editors/pending_newsletters.html",
        {"pending_newsletters": pending_newsletters},
    )


@login_required
@require_http_methods(["POST"])
def editor_approve_newsletter(request, newsletter_id):
    """
    Editor only.
    Approves a newsletter (is_approved=True) then:
    - emails subscribers (publisher + journalist subscriptions)
    - posts to X, best effort.
    No signals.

    Even if email/X fails, approval still succeeds.
    """
    if request.user.role != CustomUser.ROLE_EDITOR:
        messages.error(request, "Only editors can approve newsletters.")
        return redirect("news_app:dashboard")

    newsletter = get_object_or_404(Newsletter, id=newsletter_id)

    # If linked to a publisher, only assigned editors may approve.
    if newsletter.publisher is not None:
        is_assigned = newsletter.publisher.editors.filter(id=request.user.id).exists()
        if not is_assigned:
            messages.error(
                request,
                "You cannot approve newsletters for this publisher."
            )

            return redirect("news_app:editor_pending_newsletters")

    if newsletter.is_approved:
        messages.info(request, "That newsletter is already approved.")
        return redirect("news_app:editor_pending_newsletters")

    # Approve first
    newsletter.is_approved = True
    newsletter.save()

    # Subscribers: publisher subs + journalist subs
    subscriber_qs = CustomUser.objects.filter(role=CustomUser.ROLE_READER)

    publisher_subs = subscriber_qs.none()
    if newsletter.publisher:
        publisher_subs = subscriber_qs.filter(
            subscribed_publishers=newsletter.publisher
        )

    journalist_subs = subscriber_qs.filter(subscribed_journalists=newsletter.journalist)

    subscribers = (publisher_subs | journalist_subs).distinct()

    email_list = [u.email for u in subscribers if u.email]

    email_sent = False
    if email_list:
        subject = f"New newsletter approved: {newsletter.title}"
        body = (
            f"{newsletter.title}\n\n"
            f"{newsletter.body[:200]}...\n\n"
            f"Read it here: http://127.0.0.1:8000/newsletters/{newsletter.id}/\n"
        )

        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=email_list,
                fail_silently=False,
            )
            email_sent = True
        except Exception:
            pass

    # X post
    x_posted = False
    try:
        bearer_token = os.getenv("X_BEARER_TOKEN")
        x_post_url = os.getenv("X_POST_URL")

        if bearer_token and x_post_url:
            tweet_text = (
                f"{newsletter.title} - "
                f"http://127.0.0.1:8000/newsletters/{newsletter.id}/"
            )

            headers = {
                "Authorization": f"Bearer {bearer_token}",
                "Content-Type": "application/json",
            }
            payload = {"text": tweet_text}

            resp = requests.post(
                x_post_url,
                headers=headers,
                json=payload,
                timeout=10,
            )
            resp.raise_for_status()
            x_posted = True
    except Exception:
        pass

    messages.success(request, f"Approved: {newsletter.title}")

    if email_list:
        if email_sent:
            messages.success(request, f"Emailed {len(email_list)} subscriber(s).")
        else:
            messages.warning(request, "Newsletter approved, but email failed.")
    else:
        messages.info(request, "Newsletter approved. No subscriber emails to send.")

    if x_posted:
        messages.success(request, "Posted to X successfully.")
    else:
        if os.getenv("X_BEARER_TOKEN") and os.getenv("X_POST_URL"):
            messages.warning(request, "Newsletter approved, but X posting failed.")
        else:
            messages.info(request, "X posting not configured yet (skipped).")

    return redirect("news_app:editor_pending_newsletters")


@login_required
def my_newsletters(request):
    """
    Journalist only.
    Shows the logged-in journalist's own newsletters, approved or not.
    """
    if request.user.role != CustomUser.ROLE_JOURNALIST:
        messages.error(request, "Only journalists can access My Newsletters.")
        return redirect("news_app:dashboard")

    newsletters = Newsletter.objects.filter(
        journalist=request.user
    ).order_by("-created_at")

    return render(
        request,
        "news_app/journalists/my_newsletters.html",
        {"newsletters": newsletters},
    )


@login_required
@require_http_methods(["GET", "POST"])
def newsletter_create(request):
    """
    Journalist only.
    Newsletters created here are always drafts (is_approved=False).
    """
    if request.user.role != CustomUser.ROLE_JOURNALIST:
        messages.error(request, "Only journalists can create newsletters.")
        return redirect("news_app:dashboard")

    if request.method == "POST":
        form = NewsletterForm(request.POST, journalist_user=request.user)

        if form.is_valid():
            newsletter = form.save(commit=False)
            newsletter.journalist = request.user
            newsletter.is_approved = False
            newsletter.save()

            messages.success(
                request, "Newsletter draft created. It is not approved yet."
            )
            return redirect("news_app:my_newsletters")

        messages.error(request, "Please fix the errors below.")
    else:
        form = NewsletterForm(journalist_user=request.user)

    return render(
        request,
        "news_app/journalists/newsletter_form.html",
        {"form": form},
    )


@login_required
@require_http_methods(["GET", "POST"])
def newsletter_edit(request, newsletter_id):
    """
    Journalist only.
    Only allow editing on own newsletters.
    If approved, editing is blocked.
    """
    if request.user.role != CustomUser.ROLE_JOURNALIST:
        messages.error(request, "Only journalists can edit their newsletters.")
        return redirect("news_app:dashboard")

    newsletter = get_object_or_404(
        Newsletter, id=newsletter_id, journalist=request.user
    )

    if newsletter.is_approved:
        messages.error(
            request, "This newsletter is already approved and cannot be edited."
        )
        return redirect("news_app:my_newsletters")

    if request.method == "POST":
        form = NewsletterForm(
            request.POST,
            instance=newsletter,
            journalist_user=request.user,
        )

        if form.is_valid():
            updated_newsletter = form.save(commit=False)
            updated_newsletter.journalist = request.user
            updated_newsletter.is_approved = False
            updated_newsletter.save()

            messages.success(request, "Newsletter updated.")
            return redirect("news_app:my_newsletters")

        messages.error(request, "Please fix the errors below.")
    else:
        form = NewsletterForm(
            instance=newsletter,
            journalist_user=request.user,
        )

    return render(
        request,
        "news_app/journalists/newsletter_form.html",
        {"form": form, "newsletter": newsletter, "is_edit": True},
    )


@login_required
@require_http_methods(["POST"])
def newsletter_delete(request, newsletter_id):
    """
    Journalist only.
    Only allow deleting own newsletters.
    If approved, deleting is blocked.
    """
    if request.user.role != CustomUser.ROLE_JOURNALIST:
        messages.error(request, "Only journalists can delete newsletters.")
        return redirect("news_app:dashboard")

    newsletter = get_object_or_404(
        Newsletter, id=newsletter_id, journalist=request.user
    )

    if newsletter.is_approved:
        messages.error(
            request, "This newsletter is already approved and cannot be deleted."
        )
        return redirect("news_app:my_newsletters")

    title = newsletter.title
    newsletter.delete()
    messages.success(request, f"Deleted newsletter: {title}")
    return redirect("news_app:my_newsletters")


def newsletter_list(request):
    newsletters = Newsletter.objects.filter(is_approved=True).order_by("-created_at")
    return render(
        request,
        "news_app/newsletters/newsletter_list.html",
        {"newsletters": newsletters},
    )


def newsletter_detail(request, newsletter_id):
    newsletter = get_object_or_404(
        Newsletter, id=newsletter_id, is_approved=True
    )
    return render(
        request,
        "news_app/newsletters/newsletter_detail.html",
        {"newsletter": newsletter},
    )


@login_required
def editor_articles(request):
    """
    Editor only.
    List of articles editor is allowed to manage.
    """
    if request.user.role != CustomUser.ROLE_EDITOR:
        messages.error(request, "Only editors can access the editor dashboard.")
        return redirect("news_app:dashboard")

    allowed_publisher_ids = request.user.publishers_as_editor.values_list(
        "id", flat=True
    )

    articles = Article.objects.filter(
        models.Q(publisher__isnull=True)
        | models.Q(publisher_id__in=allowed_publisher_ids)
    ).distinct().order_by("-created_at")

    return render(
        request,
        "news_app/editors/articles_list.html",
        {"articles": articles},
    )


@login_required
@require_http_methods(["GET", "POST"])
def editor_article_edit(request, article_id):
    """
    Editor only.
    Can edit allowed articles. Approved stays approved.
    """
    if request.user.role != CustomUser.ROLE_EDITOR:
        messages.error(request, "Only editors can edit articles.")
        return redirect("news_app:dashboard")

    article = get_object_or_404(Article, id=article_id)

    if not editor_can_manage_publisher_item(request.user, article.publisher):
        messages.error(request, "You cannot edit articles for this publisher.")
        return redirect("news_app:editor_articles")

    if request.method == "POST":
        form = ArticleForm(request.POST, instance=article)

        if form.is_valid():
            updated_article = form.save(commit=False)

            # Keep original journalist ownership
            updated_article.journalist = article.journalist

            # keep approval status as is
            updated_article.is_approved = article.is_approved

            updated_article.save()
            messages.success(request, "Article updated.")
            return redirect("news_app:editor_articles")

        messages.error(request, "Please fix the errors below.")
    else:
        form = ArticleForm(instance=article)

    return render(
        request,
        "news_app/editors/article_form.html",
        {"form": form, "article": article, "is_edit": True},
    )


@login_required
@require_http_methods(["POST"])
def editor_article_delete(request, article_id):
    """
    Editor only.
    Can delete allowed articles.
    """
    if request.user.role != CustomUser.ROLE_EDITOR:
        messages.error(request, "Only editors can delete articles.")
        return redirect("news_app:dashboard")

    article = get_object_or_404(Article, id=article_id)

    if not editor_can_manage_publisher_item(request.user, article.publisher):
        messages.error(request, "You cannot delete articles for this publisher.")
        return redirect("news_app:editor_articles")

    title = article.title
    article.delete()
    messages.success(request, f"Deleted article: {title}")
    return redirect("news_app:editor_articles")


@login_required
def editor_newsletters(request):
    """
    Editor only.
    List of newsletters editor is allowed to manage.
    """
    if request.user.role != CustomUser.ROLE_EDITOR:
        messages.error(request, "Only editors can access the editor dashboard.")
        return redirect("news_app:dashboard")

    allowed_publisher_ids = request.user.publishers_as_editor.values_list(
        "id", flat=True
    )

    newsletters = Newsletter.objects.filter(
        models.Q(publisher__isnull=True)
        | models.Q(publisher_id__in=allowed_publisher_ids)
    ).distinct().order_by("-created_at")

    return render(
        request,
        "news_app/editors/newsletters_list.html",
        {"newsletters": newsletters},
    )


@login_required
@require_http_methods(["GET", "POST"])
def editor_newsletter_edit(request, newsletter_id):
    """
    Editor only.
    Can edit allowed newsletters. Approved stays approved.
    """
    if request.user.role != CustomUser.ROLE_EDITOR:
        messages.error(request, "Only editors can edit newsletters.")
        return redirect("news_app:dashboard")

    newsletter = get_object_or_404(Newsletter, id=newsletter_id)

    if not editor_can_manage_publisher_item(request.user, newsletter.publisher):
        messages.error(request, "You cannot edit newsletters for this publisher.")
        return redirect("news_app:editor_newsletters")

    if request.method == "POST":
        form = NewsletterForm(
            request.POST,
            instance=newsletter,
            journalist_user=newsletter.journalist,
        )

        if form.is_valid():
            updated_newsletter = form.save(commit=False)

            # Keep original journalist ownership
            updated_newsletter.journalist = newsletter.journalist

            # Keep approval status as-is
            updated_newsletter.is_approved = newsletter.is_approved

            updated_newsletter.save()
            messages.success(request, "Newsletter updated.")
            return redirect("news_app:editor_newsletters")

        messages.error(request, "Please fix the errors below.")
    else:
        form = NewsletterForm(
            instance=newsletter,
            journalist_user=newsletter.journalist,
        )

    return render(
        request,
        "news_app/editors/newsletter_form.html",
        {"form": form, "newsletter": newsletter, "is_edit": True},
    )


@login_required
@require_http_methods(["POST"])
def editor_newsletter_delete(request, newsletter_id):
    """
    Editor only.
    Can delete allowed newsletters.
    """
    if request.user.role != CustomUser.ROLE_EDITOR:
        messages.error(request, "Only editors can delete newsletters.")
        return redirect("news_app:dashboard")

    newsletter = get_object_or_404(Newsletter, id=newsletter_id)

    if not editor_can_manage_publisher_item(request.user, newsletter.publisher):
        messages.error(request, "You cannot delete newsletters for this publisher.")
        return redirect("news_app:editor_newsletters")

    title = newsletter.title
    newsletter.delete()
    messages.success(request, f"Deleted newsletter: {title}")
    return redirect("news_app:editor_newsletters")
