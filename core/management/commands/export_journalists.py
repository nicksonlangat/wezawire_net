from datetime import datetime

import openpyxl
from django.apps import apps
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Export all journalists as an Excel file with exact field names"

    def handle(self, *args, **kwargs):
        # Get the Journalist model
        Journalist = apps.get_model(
            "core", "Journalist"
        )  # Replace 'your_app_name' with your actual app name

        # Get field names dynamically (excluding 'id')
        field_names = [
            field.name for field in Journalist._meta.fields if field.name != "id"
        ]

        # Query all journalists
        journalists = Journalist.objects.values(*field_names)

        # Create a new Excel workbook and sheet
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Journalists"

        # Add exact field names as headers
        ws.append(field_names)

        # Add data rows while handling timezone-aware datetime fields
        for journalist in journalists:
            row = []
            for field in field_names:
                value = journalist[field]

                # If the field is a datetime, convert it to naive (remove timezone)
                if isinstance(value, datetime) and value.tzinfo is not None:
                    value = value.replace(tzinfo=None)

                row.append(value)

            ws.append(row)

        # Save to file
        file_path = "journalists.xlsx"
        wb.save(file_path)

        self.stdout.write(self.style.SUCCESS(f"Exported data saved to {file_path}"))
