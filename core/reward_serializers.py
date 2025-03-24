from rest_framework import serializers
from .models import Journalist, PressRelease
from .models import PublishedLink, PointTransaction, WithdrawalRequest


class JournalistSerializer(serializers.ModelSerializer):
    total_points = serializers.SerializerMethodField()
    points_in_ksh = serializers.SerializerMethodField()
    
    class Meta:
        model = Journalist
        fields = ['id', 'email', 'name', 'phone', 'country', 
                  'title', 'media_house', 'total_points', 'points_in_ksh']
    
    def get_total_points(self, obj):
        return obj.current_points
    
    def get_points_in_ksh(self, obj):
        return obj.points_in_ksh


class PressReleaseSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    
    class Meta:
        model = PressRelease
        fields = ['id', 'title', 'description', 'client', 
                  'country', 'is_published', 'author_name', 'created_at']
    
    def get_author_name(self, obj):
        return obj.author.get_full_name() if obj.author else None


class PublishedLinkSerializer(serializers.ModelSerializer):
    journalist_name = serializers.SerializerMethodField(read_only=True)
    press_release_title = serializers.SerializerMethodField(read_only=True)
    reviewer_name = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = PublishedLink
        fields = [
            'id', 'journalist', 'journalist_name', 'press_release', 'press_release_title',
            'url', 'title', 'publication_date', 'status', 'notes',
            'reviewed_by', 'reviewer_name', 'reviewed_at', 'created_at'
        ]
        read_only_fields = ['journalist', 'reviewed_by', 'reviewed_at', 'status']
    
    def get_journalist_name(self, obj):
        return obj.journalist.name if obj.journalist else None
    
    def get_press_release_title(self, obj):
        return obj.press_release.title if obj.press_release else None
    
    def get_reviewer_name(self, obj):
        return f"{obj.reviewed_by.first_name} {obj.reviewed_by.last_name}" if obj.reviewed_by else None


class PointTransactionSerializer(serializers.ModelSerializer):
    journalist_name = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = PointTransaction
        fields = [
            'id', 'journalist', 'journalist_name', 'points', 'transaction_type',
            'description', 'related_press_release', 'created_at'
        ]
        read_only_fields = ['journalist', 'points', 
                            'transaction_type', 'description', 'related_press_release']
    
    def get_journalist_name(self, obj):
        return obj.journalist.name if obj.journalist else None


class WithdrawalRequestSerializer(serializers.ModelSerializer):
    journalist_name = serializers.SerializerMethodField(read_only=True)
    processor_name = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = WithdrawalRequest
        fields = [
            'id', 'journalist', 'journalist_name', 'points', 'amount', 'status',
            'payment_method', 'payment_details', 'processed_by', 'processor_name',
            'processed_at', 'transaction_reference', 'notes', 'created_at'
        ]
        read_only_fields = ['journalist', 'amount',
                             'status', 'processed_by', 'processed_at', 'transaction_reference']
    
    def get_journalist_name(self, obj):
        return obj.journalist.name if obj.journalist else None
    
    def get_processor_name(self, obj):
        return obj.processed_by.first_name if obj.processed_by else None


class JournalistDashboardSerializer(serializers.Serializer):
    journalist = JournalistSerializer()
    press_releases = PressReleaseSerializer(many=True)
    published_links = PublishedLinkSerializer(many=True)
    total_points = serializers.IntegerField()
    points_in_ksh = serializers.DecimalField(max_digits=10, decimal_places=2)
    withdrawal_requests = WithdrawalRequestSerializer(many=True)


class PressReleaseWithLinksSerializer(serializers.ModelSerializer):
    published_links = serializers.SerializerMethodField()
    
    class Meta:
        model = PressRelease
        fields = ['id', 'title', 'description', 'client', 'country', 'is_published', 'published_links', 'created_at']
    
    def get_published_links(self, obj):
        links = obj.published_links.all()
        return PublishedLinkSerializer(links, many=True).data
