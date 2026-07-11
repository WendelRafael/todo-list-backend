from rest_framework import generics, status
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .serializers import (
    PasswordChangeSerializer,
    RegisterSerializer,
    UserSerializer,
)


class RegisterRateThrottle(AnonRateThrottle):
    """Limita criações de conta por IP (anti-spam de registros).

    A taxa vem de DEFAULT_THROTTLE_RATES["register"] no settings — desligada
    em desenvolvimento (DEBUG=True), ativa só com a API publicada.
    """

    scope = "register"


class LoginRateThrottle(AnonRateThrottle):
    """Limita tentativas de login por IP (anti força bruta de senhas).

    A taxa vem de DEFAULT_THROTTLE_RATES["login"] no settings — desligada
    em desenvolvimento (DEBUG=True), ativa só com a API publicada.
    """

    scope = "login"


class PasswordChangeView(APIView):
    """POST /api/auth/password/ — altera a senha do usuário autenticado.

    O token atual continua válido: a sessão do app não cai após a troca.
    """

    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveAPIView):
    """GET /api/auth/me/ — dados do usuário autenticado (nome e e-mail)."""

    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/ — cria a conta (rota pública por definição)."""

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_classes = [RegisterRateThrottle]


class LoginView(ObtainAuthToken):
    """POST /api/auth/login/ — valida credenciais e retorna token + dados do usuário."""

    permission_classes = [AllowAny]
    # ObtainAuthToken zera os throttles por padrão — reativa o limite por IP.
    throttle_classes = [LoginRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {"token": token.key, "user": {"id": user.id, "username": user.username}}
        )


class LogoutView(APIView):
    """POST /api/auth/logout/ — apaga o token do usuário no servidor."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
