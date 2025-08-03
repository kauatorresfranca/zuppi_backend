from rest_framework import serializers
from django.utils.text import slugify
import os
from .models import CustomUser  # Alterado de Profile para CustomUser

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser  # Alterado de Profile para CustomUser
        fields = ["username", "bio", "profile_picture"]

    def validate_profile_picture(self, value):
        if value:
            # Sanitizar o nome do arquivo
            original_name = value.name
            name, ext = os.path.splitext(original_name)
            sanitized_name = f"{slugify(name)}{ext.lower()}"
            value.name = sanitized_name
            return value
        return value