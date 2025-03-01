from django.urls import path

from . import journalists
from .views import (
    ClientDetailView,
    ClientListView,
    GeneratePressReleaseAPI,
    JournalistDetailView,
    PressDistribute,
    PressPreview,
    PressReleaseDetailView,
    PressReleaseListCreateView,
    StreamOpenAIResponseView,
    index,
    stream_opena_response,
)

urlpatterns = [
    path("", index),
    path(
        "press-releases/",
        PressReleaseListCreateView.as_view(),
        name="press-release-list-create",
    ),
    path(
        "press-releases/<uuid:pk>/",
        PressReleaseDetailView.as_view(),
        name="press-release-detail",
    ),
    path(
        "preview-press-release/",
        PressPreview.as_view(),
        name="press-release-preview",
    ),
    path(
        "distribute-press-release/",
        PressDistribute.as_view(),
        name="press-release-preview",
    ),
    path("answer", stream_opena_response),
    path("ai-answer", StreamOpenAIResponseView.as_view()),
    path("generate-press-release/", GeneratePressReleaseAPI.as_view()),
    path("clients/", ClientListView.as_view(), name="clients"),
    path("clients/<uuid:pk>/", ClientDetailView.as_view(), name="client-detail"),
    path(
        "journalists/", journalists.JournalistListView.as_view(), name="journalist-list"
    ),
    path(
        "journalists/<uuid:pk>/",
        JournalistDetailView.as_view(),
        name="journalist-detail",
    ),
    path(
        "upload/",
        journalists.JournalistBulkUploadView.as_view(),
        name="journalist-upload",
    ),
]
