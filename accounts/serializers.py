from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    """Dados públicos do próprio usuário (GET /api/auth/me/)."""

    class Meta:
        model = User
        fields = ["id", "username", "email"]


class RegisterSerializer(serializers.ModelSerializer):
    """Cria a conta do usuário validando força da senha e e-mail único."""

    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Já existe uma conta com este e-mail.")
        return value

    def create(self, validated_data):
        # create_user garante a senha armazenada com hash, nunca em texto plano
        return User.objects.create_user(**validated_data)
