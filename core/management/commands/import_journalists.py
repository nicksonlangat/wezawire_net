import csv
import os

from django.core.management.base import BaseCommand

from ...models import Journalist


class Command(BaseCommand):
    help = "Import journalists from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to the CSV file")

    def handle(self, *args, **options):
        csv_file_path = options["csv_file"]

        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f"File not found: {csv_file_path}"))
            return

        with open(csv_file_path, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            # Normalize column names (remove spaces)
            reader.fieldnames = [col.strip() for col in reader.fieldnames]

            for row in reader:
                # Strip whitespace from values
                # Media House,Name of Contact,Designation ,Contact ,Email

                email = row.get("Email", "").strip()
                name = row.get("Name of Contact", "").strip()
                phone = row.get("Contact", "").strip()
                title = row.get("Designation", "").strip()
                media_house = row.get("Media House", "").strip()

                if not email:
                    self.stdout.write(
                        self.style.WARNING("Skipping row with missing email")
                    )
                    continue

                journalist, created = Journalist.objects.update_or_create(
                    email=email,
                    defaults={
                        "name": name or None,
                        "phone": phone or None,
                        "title": title or None,
                        "media_house": media_house or None,
                        "country": "Zambia",
                    },
                )

                action = "Created" if created else "Updated"
                self.stdout.write(self.style.SUCCESS(f"{action} journalist: {email}"))

        self.stdout.write(self.style.SUCCESS("Import complete!"))
