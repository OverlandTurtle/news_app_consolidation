import base64
from django.test import TestCase
from rest_framework.test import APIClient
from .models import Article, CustomUser, Publisher


# Create your tests here.
class ApiTests(TestCase):
    """
    API tests for:
    - GET /api/me/feed/
    - GET /api/articles/<id>/

    Auth method: BasicAuth.
    """

    def setUp(self):
        self.client = APIClient()

        # Users
        self.reader = CustomUser.objects.create_user(
            username="test_reader",
            password="readerpass123",
            role=CustomUser.ROLE_READER,
            email="reader@test.com",
        )

        self.editor = CustomUser.objects.create_user(
            username="test_editor",
            password="editorpass123",
            role=CustomUser.ROLE_EDITOR,
            email="editor@test.com",
        )

        self.journalist1 = CustomUser.objects.create_user(
            username="test_journalist1",
            password="journalistpass123",
            role=CustomUser.ROLE_JOURNALIST,
            email="j1@test.com",
        )

        self.journalist2 = CustomUser.objects.create_user(
            username="test_journalist2",
            password="journalistpass123",
            role=CustomUser.ROLE_JOURNALIST,
            email="j2@test.com",
        )

        # Publishers
        self.publisher_a = Publisher.objects.create(name="Publisher Alpha")
        self.publisher_b = Publisher.objects.create(name="Publisher Beta")

        # Articles (approved and unapproved)
        self.article_a1 = Article.objects.create(
            publisher=self.publisher_a,
            journalist=self.journalist1,
            title="Article A1 Title",
            summary="A1 summary",
            body="A1 body text that is definitely"
            "long enough for the test purposes.",
            is_approved=True,
        )

        self.article_a2_unapproved = Article.objects.create(
            publisher=self.publisher_a,
            journalist=self.journalist1,
            title="Article A2 Draft",
            summary="Draft",
            body="Draft body text that is definitely"
            "long enough for the test purposes.",
            is_approved=False,
        )

        self.article_b1 = Article.objects.create(
            publisher=self.publisher_b,
            journalist=self.journalist2,
            title="Article B1 Title",
            summary="B1 summary",
            body="B1 body text that is definitely"
            " long enough for the test purposes.",
            is_approved=True,
        )

    def auth_as(self, username: str, password: str):
        """
        Sets the BasicAuth header for the API client.
        """
        token_bytes = f"{username}:{password}".encode("utf-8")
        b64 = base64.b64encode(token_bytes).decode("utf-8")
        self.client.credentials(HTTP_AUTHORIZATION=f"Basic {b64}")

    def clear_auth(self):
        """
        Clears auth for testing 401 responses.
        """
        self.client.credentials()

    # ----------------------
    # GET /api/me/feed/
    # ----------------------
    def test_feed_requires_auth(self):
        self.clear_auth()
        resp = self.client.get("/api/me/feed/")
        self.assertEqual(resp.status_code, 401)

    def test_feed_reader_no_subscriptions_empty(self):
        self.auth_as("test_reader", "readerpass123")
        resp = self.client.get("/api/me/feed/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["ok"])
        self.assertEqual(resp.data["count"], 0)
        self.assertEqual(resp.data["data"], [])

    def test_feed_reader_publisher_subscription_returns_match_approved_only(self):
        # Subscribe reader to Publisher A
        self.reader.subscribed_publishers.add(self.publisher_a)

        self.auth_as("test_reader", "readerpass123")
        resp = self.client.get("/api/me/feed/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["ok"])

        returned_ids = [item["id"] for item in resp.data["data"]]

        # Approved + matching publisher should be included
        self.assertIn(self.article_a1.id, returned_ids)

        # Unapproved should never show up in the feed
        self.assertNotIn(self.article_a2_unapproved.id, returned_ids)

        # Different publisher should not show up
        self.assertNotIn(self.article_b1.id, returned_ids)

    def test_feed_reader_journalist_subscription_returns_matching_approved(self):
        # Subscribe reader to Journalist 2
        self.reader.subscribed_journalists.add(self.journalist2)

        self.auth_as("test_reader", "readerpass123")
        resp = self.client.get("/api/me/feed/")
        self.assertEqual(resp.status_code, 200)

        returned_ids = [item["id"] for item in resp.data["data"]]
        self.assertIn(self.article_b1.id, returned_ids)
        self.assertNotIn(self.article_a1.id, returned_ids)

    def test_feed_reader_union_of_subscriptions(self):
        self.reader.subscribed_publishers.add(self.publisher_a)
        self.reader.subscribed_journalists.add(self.journalist2)

        self.auth_as("test_reader", "readerpass123")
        resp = self.client.get("/api/me/feed/")
        self.assertEqual(resp.status_code, 200)

        returned_ids = [item["id"] for item in resp.data["data"]]
        self.assertIn(self.article_a1.id, returned_ids)
        self.assertIn(self.article_b1.id, returned_ids)

    def test_feed_non_reader_forbidden(self):
        self.auth_as("test_editor", "editorpass123")
        resp = self.client.get("/api/me/feed/")
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(resp.data["ok"])

    # ----------------------------
    # GET /api/articles/<id>/
    # ----------------------------
    def test_detail_requires_auth(self):
        self.clear_auth()
        resp = self.client.get(f"/api/articles/{self.article_a1.id}/")
        self.assertEqual(resp.status_code, 401)

    def test_detail_reader_allowed_returns_200(self):
        # Make the article "allowed" via publisher subscription
        self.reader.subscribed_publishers.add(self.publisher_a)

        self.auth_as("test_reader", "readerpass123")
        resp = self.client.get(f"/api/articles/{self.article_a1.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["ok"])
        self.assertEqual(resp.data["data"]["id"], self.article_a1.id)

    def test_detail_reader_not_subscribed_returns_404(self):
        self.auth_as("test_reader", "readerpass123")
        resp = self.client.get(f"/api/articles/{self.article_a1.id}/")
        self.assertEqual(resp.status_code, 404)

    def test_detail_reader_subscribed_but_unapproved_returns_404(self):
        self.reader.subscribed_publishers.add(self.publisher_a)

        self.auth_as("test_reader", "readerpass123")
        resp = self.client.get(f"/api/articles/{self.article_a2_unapproved.id}/")
        self.assertEqual(resp.status_code, 404)

    def test_detail_non_reader_forbidden(self):
        self.auth_as("test_editor", "editorpass123")
        resp = self.client.get(f"/api/articles/{self.article_a1.id}/")
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(resp.data["ok"])
