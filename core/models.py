from django.db import models

from accounts.models import User
from common.models import BaseModel


class Client(BaseModel):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=250, blank=True, null=True)
    phone = models.CharField(max_length=250, blank=True, null=True)
    country = models.CharField(max_length=250, blank=True, null=True)
    website = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    logo = models.ImageField(upload_to="clients", null=True, blank=True)
    about = models.TextField(blank=True, null=True)
    def __str__(self) -> str:
        return str(self.email)



class JournalistPointsManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().annotate(
            total_points=models.Sum(
                models.Case(
                    models.When(point_transactions__isnull=False, then=models.F('point_transactions__points')),
                    default=0,
                    output_field=models.IntegerField()
                )
            )
        )

class Journalist(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name="journalist")
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=250, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    country = models.CharField(max_length=250, blank=True, null=True)
    title = models.CharField(max_length=250, blank=True, null=True)
    media_house = models.TextField(blank=True, null=True)

    objects = models.Manager()
    with_points = JournalistPointsManager()
    
    @property
    def current_points(self):
        earned = self.point_transactions.filter(transaction_type='earned').aggregate(
            total=models.Sum('points'))['total'] or 0
        withdrawn = self.point_transactions.filter(transaction_type='withdrawal').aggregate(
            total=models.Sum('points'))['total'] or 0
        return earned - abs(withdrawn)
    
    @property
    def points_in_ksh(self):
        return (self.current_points / 5) * 100  # 5 points = 100 KSH

    def __str__(self) -> str:
        return str(self.email)


class PressRelease(BaseModel):
    author = models.ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="press_releases",
    )
    title = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    client = models.TextField(blank=True, null=True)
    partner = models.TextField(blank=True, null=True)
    country = models.TextField(blank=True, null=True)
    additional_data = models.JSONField(blank=True, null=True)
    json_content = models.JSONField(blank=True, null=True)
    is_published = models.BooleanField(default=False)
    shared_with = models.ManyToManyField(
        Journalist, blank=True, related_name="shared_press_releases"
    )

    def __str__(self) -> str:
        return str(self.title)

class Partner(BaseModel):
    name = models.CharField(max_length=250, blank=True, null=True)
    press_release = models.ForeignKey(PressRelease, null=True, blank=True, on_delete=models.CASCADE, related_name='partners')
    image = models.ImageField(upload_to="partners", null=True, blank=True)
    
    def __str__(self) -> str:
        return str(self.name)



class PublishedLink(BaseModel):
    journalist = models.ForeignKey(
        Journalist,
        on_delete=models.CASCADE,
        related_name="published_links"
    )
    press_release = models.ForeignKey(
        PressRelease,
        on_delete=models.CASCADE,
        related_name="published_links"
    )
    url = models.URLField()
    title = models.CharField(max_length=255, blank=True, null=True)
    publication_date = models.DateField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending Review'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected')
        ],
        default='pending'
    )
    notes = models.TextField(blank=True, null=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_links"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.journalist.name} - {self.press_release.title[:30]}"


class PointTransaction(BaseModel):
    journalist = models.ForeignKey(
        Journalist,
        on_delete=models.CASCADE,
        related_name="point_transactions"
    )
    points = models.IntegerField()  # Positive for earnings, negative for withdrawals
    transaction_type = models.CharField(
        max_length=20,
        choices=[
            ('earned', 'Points Earned'),
            ('withdrawal', 'Points Withdrawal')
        ]
    )
    description = models.TextField(blank=True, null=True)
    related_press_release = models.ForeignKey(
        PressRelease,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="point_transactions"
    )
    related_links = models.ManyToManyField(
        PublishedLink,
        blank=True,
        related_name="point_transactions"
    )

    def __str__(self):
        return f"{self.journalist.name} - {self.points} points - {self.transaction_type}"


class WithdrawalRequest(BaseModel):
    journalist = models.ForeignKey(
        Journalist,
        on_delete=models.CASCADE,
        related_name="withdrawal_requests"
    )
    points = models.IntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # In KSH
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('completed', 'Completed')
        ],
        default='pending'
    )
    payment_method = models.CharField(max_length=50)  # e.g., "M-Pesa", "Bank Transfer"
    payment_details = models.JSONField(blank=True, null=True)  # Store phone number or bank account details
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_withdrawals"
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    transaction_reference = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.journalist.name} - {self.points} points - {self.amount} KSH"
