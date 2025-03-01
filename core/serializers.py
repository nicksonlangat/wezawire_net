from rest_framework import serializers

from .models import Client, Journalist, PressRelease


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = "__all__"


class PressReleaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = PressRelease
        fields = "__all__"

    def to_representation(self, instance):
        """Customize shared_with field serialization using JournalistSerializer."""
        representation = super().to_representation(instance)
        representation["shared_with"] = JournalistSerializer(
            instance.shared_with.all(), many=True
        ).data
        return representation


class JournalistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Journalist
        fields = "__all__"
