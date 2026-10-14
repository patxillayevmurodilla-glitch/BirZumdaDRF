from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from app.models import Product, Blog, User


class BlogModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Blog
        fields = "__all__"


class ProductModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        trim_whitespace=False
    )

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "password"]
        read_only_fields = ["id"]

    def validate_email(self, value):
        return value.strip().lower()

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class VerifyEmailSerializer(serializers.Serializer):
    pre_token = serializers.CharField()
    code = serializers.RegexField(
        regex=r"^\d{6}$",
        error_messages={
            "invalid": "Kod 6 ta raqamdan iborat bo'lishi kerak."
        }
    )


class ResendCodeSerializer(serializers.Serializer):
    pre_token = serializers.CharField()


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.RegexField(
        regex=r"^\d{6}$",
        error_messages={
            "invalid": "Kod 6 ta raqamdan iborat bo'lishi kerak."
        }
    )
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        trim_whitespace=False
    )

    def validate_email(self, value):
        return value.strip().lower()

    def validate_new_password(self, value):
        validate_password(value)
        return value
