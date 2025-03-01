from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    def create_user(self, email, password, **extra_fields):
        first_name = extra_fields.get("first_name", None)
        last_name = extra_fields.get("last_name", None)

        if not email:
            raise ValueError("Email is required.")

        if not first_name:
            raise ValueError("First name is required.")
        if not last_name:
            raise ValueError("Last name is required.")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()

        return user

    def create_superuser(self, email, password, **extra_fields):
        first_name = extra_fields.get("first_name", None)
        last_name = extra_fields.get("last_name", None)

        if not email:
            raise ValueError("Email is required.")

        if not first_name:
            raise ValueError("First name is required.")
        if not last_name:
            raise ValueError("Last name is required.")

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must be staff.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must be superuser")

        return self.create_user(email, password, **extra_fields)
