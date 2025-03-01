from django.apps import apps
from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered

# Get all models from the installed apps
models = apps.get_models()

# Loop through the models and register each one
for model in models:
    try:
        admin.site.register(model)
    except AlreadyRegistered:
        # If the model is already registered, skip it
        pass
