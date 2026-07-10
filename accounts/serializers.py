from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    """Dados públicos do próprio usuário (GET /api/auth/me/)."""

    class Meta:
        model = User
        fields = ["id", "username", "email"]


class PasswordChangeSerializer(serializers.Serializer):
    """Troca de senha do usuário logado: exige a senha atual correta."""

    old_password = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )
    new_password = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )

    def validate_old_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Senha atual incorreta.")
        return value

    def validate_new_password(self, value):
        # Passa o usuário para os validadores (ex.: similaridade com username)
        validate_password(value, self.context["request"].user)
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user


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
