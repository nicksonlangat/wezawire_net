from django.db import models

from accounts.models import User
from common.models import BaseModel


class Client(BaseModel):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=250, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    country = models.CharField(max_length=250, blank=True, null=True)
    website = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self) -> str:
        return str(self.email)


class Journalist(BaseModel):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=250, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    country = models.CharField(max_length=250, blank=True, null=True)
    title = models.CharField(max_length=250, blank=True, null=True)
    media_house = models.TextField(blank=True, null=True)

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
