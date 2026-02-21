from rest_framework import serializers
from .models import Article


class ArticleFeedSerializer(serializers.ModelSerializer):
    """
    Serializer for Reader feed endpoint.
    """

    publisher_name = serializers.SerializerMethodField()
    journalist_username = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = [
            "id",
            "title",
            "summary",
            "body",
            "publisher_name",
            "journalist_username",
            "created_at",
        ]

    def get_publisher_name(self, obj):
        if obj.publisher:
            return obj.publisher.name
        return None

    def get_journalist_username(self, obj):
        return obj.journalist.username
