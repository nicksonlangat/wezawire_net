from accounts.models import User
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Sum, Count, F
from django.db import transaction

# from accounts.permissions import IsAdmin
from .models import Journalist, PressRelease, PublishedLink, PointTransaction, WithdrawalRequest
from .reward_serializers import (
    PublishedLinkSerializer, 
    PointTransactionSerializer, 
    WithdrawalRequestSerializer,
    JournalistDashboardSerializer,
    PressReleaseWithLinksSerializer
)


class JournalistDashboardAPIView(APIView):
    permission_classes = [] #permissions.IsAuthenticated
    authentication_classes = []

    def get(self, request, format=None):
        try:
            # journalist = request.user.journalist
            journalist = Journalist.objects.filter(email="nickson@wezaprosoft.com").first()
        except:
            return Response({"error": "User is not a journalist"}, status=status.HTTP_403_FORBIDDEN)
        
        # Get press releases shared with the journalist
        press_releases = journalist.shared_press_releases.all()
        
        # Get published links and their status
        published_links = journalist.published_links.all()
        
        # Get points information
        total_points = journalist.current_points
        points_in_ksh = journalist.points_in_ksh
        
        # Get withdrawal requests
        withdrawal_requests = journalist.withdrawal_requests.all()
        
        serializer = JournalistDashboardSerializer({
            'journalist': journalist,
            'press_releases': press_releases,
            'published_links': published_links,
            'total_points': total_points,
            'points_in_ksh': points_in_ksh,
            'withdrawal_requests': withdrawal_requests
        })
        
        return Response(serializer.data)


class PublishedLinkViewSet(viewsets.ModelViewSet):
    serializer_class = PublishedLinkSerializer
    
    def get_queryset(self):
        # if self.request.user.is_staff:
        return PublishedLink.objects.all()
        # try:
        #     journalist = self.request.user.journalist
        #     return journalist.published_links.all()
        # except:
        #     return PublishedLink.objects.none()
    
    def perform_create(self, serializer):
        try:
            # journalist = self.request.user.journalist
            journalist = Journalist.objects.filter(email="nickson@wezaprosoft.com").first()
            serializer.save(journalist=journalist)
        except:
            raise PermissionError("User is not a journalist")
    
    @action(detail=True, methods=['post'],
            #  permission_classes=[permissions.IsAdminUser]
             )
    def approve(self, request, pk=None):
        link = self.get_object()
        
        if link.status != 'pending':
            return Response({
                "error": f"Link is already {link.status}"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            # Update link status
            link.status = 'approved'
            link.reviewed_by = User.objects.get(email="nick@gmail.com")  #request.user
            link.reviewed_at = timezone.now()
            link.save()
            
            # Check if this is the first approved link for this press release
            approved_links_count = PublishedLink.objects.filter(
                journalist=link.journalist,
                press_release=link.press_release,
                status='approved'
            ).count()
            
            # Only award points for the first approved link per press release
            if approved_links_count == 1:
                # Create point transaction
                point_transaction = PointTransaction.objects.create(
                    journalist=link.journalist,
                    points=5,  # 5 points for an approved link
                    transaction_type='earned',
                    description=f"Points earned for publishing {link.press_release.title}",
                    related_press_release=link.press_release
                )
                point_transaction.related_links.add(link)
        
        return Response({
            "message": "Link approved and points awarded",
            "status": link.status
        })
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def reject(self, request, pk=None):
        link = self.get_object()
        
        if link.status != 'pending':
            return Response({
                "error": f"Link is already {link.status}"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        link.status = 'rejected'
        link.reviewed_by = request.user
        link.reviewed_at = timezone.now()
        link.notes = request.data.get('notes', '')
        link.save()
        
        return Response({
            "message": "Link rejected",
            "status": link.status
        })


class WithdrawalRequestViewSet(viewsets.ModelViewSet):
    serializer_class = WithdrawalRequestSerializer

    permission_classes = []
    authentication_classes = []
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return WithdrawalRequest.objects.all()
        try:
            journalist = Journalist.objects.filter(email="nickson@wezaprosoft.com").first()  #self.request.user.journalist
            return journalist.withdrawal_requests.all()
        except:
            return WithdrawalRequest.objects.none()
    
    def perform_create(self, serializer):
        try:
            journalist = Journalist.objects.filter(email="nickson@wezaprosoft.com").first() #self.request.user.journalist
            points_to_withdraw = serializer.validated_data['points']
            
            # Check if journalist has enough points
            if journalist.current_points < points_to_withdraw:
                raise ValueError(f"Insufficient points. You have {journalist.current_points} points.")
            
            # Calculate KSH amount
            amount = (points_to_withdraw / 5) * 100  # 5 points = 100 KSH
            
            serializer.save(journalist=journalist, amount=amount)
        except Exception as e:
            raise ValueError(str(e))
    
    @action(detail=True, methods=['post'], 
            # permission_classes=[permissions.IsAdminUser]
            )
    def process(self, request, pk=None):
        withdrawal = self.get_object()
        status_action = request.data.get('status')
        
        if status_action not in ['approved', 'rejected', 'completed']:
            return Response({
                "error": "Invalid status. Use 'approved', 'rejected', or 'completed'."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if withdrawal.status != 'pending' and status_action == 'approved':
            return Response({
                "error": f"Withdrawal request is already {withdrawal.status}"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            withdrawal.status = status_action
            withdrawal.processed_by =  User.objects.get(email="nick@gmail.com") #request.user
            withdrawal.processed_at = timezone.now()
            withdrawal.notes = request.data.get('notes', withdrawal.notes)
            
            if status_action == 'completed':
                withdrawal.transaction_reference = request.data.get('transaction_reference', '')
                
                # Create a negative point transaction for the withdrawal
                PointTransaction.objects.create(
                    journalist=withdrawal.journalist,
                    points=-withdrawal.points,  # Negative points for withdrawal
                    transaction_type='withdrawal',
                    description=f"Points withdrawn - {withdrawal.amount} KSH",
                )
            
            withdrawal.save()
        
        return Response({
            "message": f"Withdrawal request {status_action}",
            "status": withdrawal.status
        })


class AdminDashboardAPIView(APIView):
    permission_classes = []
    authentication_classes = []
    
    def get(self, request, format=None):
        # Pending links for review
        pending_links = PublishedLink.objects.filter(status='pending').count()
        
        # Pending withdrawal requests
        pending_withdrawals = WithdrawalRequest.objects.filter(status='pending').count()
        
        # Total points awarded
        total_points_awarded = PointTransaction.objects.filter(
            transaction_type='earned'
        ).aggregate(total=Sum('points'))['total'] or 0
        
        # Total points withdrawn
        total_points_withdrawn = PointTransaction.objects.filter(
            transaction_type='withdrawal'
        ).aggregate(total=Sum('points'))['total'] or 0
        
        # Total KSH paid/pending
        total_ksh_processed = WithdrawalRequest.objects.filter(
            status__in=['approved', 'completed']
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Top journalists by points
        top_journalists = Journalist.with_points.all().order_by('-total_points')[:10]
        
        return Response({
            'pending_links': pending_links,
            'pending_withdrawals': pending_withdrawals,
            'total_points_awarded': total_points_awarded,
            'total_points_withdrawn': abs(total_points_withdrawn),
            'total_ksh_processed': total_ksh_processed,
            'top_journalists': [
                {
                    'name': j.name if j.name else j.email,
                    'email': j.email,
                    'points': j.total_points
                } for j in top_journalists
            ]
        })


class PressReleaseStatsAPIView(APIView):
    permission_classes = []
    authentication_classes = []
    
    def get(self, request, pk=None):
        try:
            press_release = PressRelease.objects.get(pk=pk)
            
            # Get links stats
            links_stats = press_release.published_links.values('status').annotate(
                count=Count('id')
            )
            
            # Get journalist engagement
            journalists_shared = press_release.shared_with.count()
            journalists_published = press_release.published_links.values(
                'journalist'
            ).distinct().count()
            
            # Calculate engagement rate
            engagement_rate = 0
            if journalists_shared > 0:
                engagement_rate = (journalists_published / journalists_shared) * 100
            
            serializer = PressReleaseWithLinksSerializer(press_release)
            
            return Response({
                'press_release': serializer.data,
                'links_stats': links_stats,
                'journalists_shared': journalists_shared,
                'journalists_published': journalists_published,
                'engagement_rate': engagement_rate
            })
        except PressRelease.DoesNotExist:
            return Response({
                "error": "Press release not found"
            }, status=status.HTTP_404_NOT_FOUND)