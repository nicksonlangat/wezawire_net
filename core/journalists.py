import pandas as pd
from django.db import transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Journalist
from .serializers import JournalistSerializer


class JournalistListView(APIView):
    """
    API endpoint to list journalists with pagination and search functionality.
    """

    pagination_class = PageNumberPagination

    def get(self, request):
        queryset = Journalist.objects.all()

        # Searching functionality (email, name, country, title, media_house)
        search_query = request.query_params.get("search", None)
        if search_query:
            queryset = queryset.filter(
                Q(email__icontains=search_query)
                | Q(name__icontains=search_query)
                | Q(country__icontains=search_query)
                | Q(title__icontains=search_query)
                | Q(media_house__icontains=search_query)
            )

        # Apply pagination
        paginator = self.pagination_class()
        paginated_queryset = paginator.paginate_queryset(queryset, request)

        # Serialize data
        serializer = JournalistSerializer(paginated_queryset, many=True)
        return paginator.get_paginated_response(serializer.data)


class JournalistBulkUploadView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request, format=None):
        excel_file = request.FILES.get("file")

        if not excel_file:
            return Response(
                {"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Check file extension
        if not excel_file.name.endswith((".xls", ".xlsx")):
            return Response(
                {"error": "File must be an Excel file (.xls or .xlsx)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Read Excel file
            df = pd.read_excel(excel_file)

            # Basic validation - ensure required fields exist
            if "email" not in df.columns:
                return Response(
                    {"error": "Excel file must contain an email column"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Clean data - replace NaN with None
            df = df.where(pd.notnull(df), None)

            # Track results
            created_count = 0
            updated_count = 0
            failed_entries = []

            # Use transaction to ensure database consistency
            with transaction.atomic():
                for _, row in df.iterrows():
                    try:
                        # Convert row to dict
                        journalist_data = {
                            "email": row.get("email"),
                            "name": row.get("name"),
                            "phone": row.get("phone"),
                            "country": row.get("country"),
                            "title": row.get("title"),
                            "media_house": row.get("media_house"),
                        }

                        # Check if email is valid
                        if not journalist_data["email"] or pd.isna(
                            journalist_data["email"]
                        ):
                            failed_entries.append(
                                {"row": dict(row), "reason": "Missing or invalid email"}
                            )
                            continue

                        # Try to update existing record, create if it doesn't exist
                        journalist, created = Journalist.objects.update_or_create(
                            email=journalist_data["email"], defaults=journalist_data
                        )

                        if created:
                            created_count += 1
                        else:
                            updated_count += 1

                    except Exception as e:
                        failed_entries.append({"row": dict(row), "reason": str(e)})

            return Response(
                {
                    "success": True,
                    "created": created_count,
                    "updated": updated_count,
                    "failed": len(failed_entries),
                    "failed_entries": failed_entries[:10]
                    if failed_entries
                    else [],  # Limit to first 10 failures
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": f"Failed to process Excel file: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
