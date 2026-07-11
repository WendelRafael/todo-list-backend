"""Testes das ações de conta: registro, login, perfil, troca de senha e logout."""

from django.contrib.auth.models import User
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.views import LoginRateThrottle, RegisterRateThrottle


class RegisterTests(APITestCase):
    """POST /api/auth/register/ — criação de conta."""

    def test_registro_cria_usuario_com_senha_hasheada(self):
        """Registro válido responde 201 sem expor a senha; no banco ela vira
        hash (nunca texto puro) e continua conferindo no check_password."""
        response = self.client.post(
            reverse("register"),
            {
                "username": "wendel",
                "email": "wendel@example.com",
                "password": "senha-forte-123",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("password", response.data)
        user = User.objects.get(username="wendel")
        self.assertNotEqual(user.password, "senha-forte-123")
        self.assertTrue(user.check_password("senha-forte-123"))

    def test_registro_rejeita_senha_fraca(self):
        """Senha fraca é barrada pelos validadores do Django (400) e nenhum
        usuário é criado no banco."""
        response = self.client.post(
            reverse("register"),
            {"username": "wendel", "email": "wendel@example.com", "password": "123"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username="wendel").exists())

    def test_registro_rejeita_email_duplicado(self):
        """E-mail já cadastrado não pode gerar uma segunda conta: 400."""
        User.objects.create_user(
            "outro", email="wendel@example.com", password="senha-forte-123"
        )
        response = self.client.post(
            reverse("register"),
            {
                "username": "wendel",
                "email": "wendel@example.com",
                "password": "senha-forte-123",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginTests(APITestCase):
    """POST /api/auth/login/ — autenticação por token."""

    def setUp(self):
        self.user = User.objects.create_user(
            "wendel", email="wendel@example.com", password="senha-forte-123"
        )

    def test_login_retorna_token_e_dados_do_usuario(self):
        """Credenciais corretas respondem 200 com o token e os dados básicos
        do usuário; o token fica registrado no banco."""
        response = self.client.post(
            reverse("login"), {"username": "wendel", "password": "senha-forte-123"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
        self.assertEqual(response.data["user"]["username"], "wendel")
        self.assertTrue(Token.objects.filter(user=self.user).exists())

    def test_login_rejeita_senha_errada(self):
        """Senha errada responde 400 e nenhum token é emitido."""
        response = self.client.post(
            reverse("login"), {"username": "wendel", "password": "senha-errada"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn("token", response.data)


class MeTests(APITestCase):
    """GET /api/auth/me/ — dados do usuário logado."""

    def setUp(self):
        self.user = User.objects.create_user(
            "wendel", email="wendel@example.com", password="senha-forte-123"
        )
        self.token = Token.objects.create(user=self.user)

    def test_me_retorna_nome_e_email_do_usuario_logado(self):
        """Com token válido, o perfil devolve o username e o e-mail do dono
        do token — o que a tela de Perfil exibe."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "wendel")
        self.assertEqual(response.data["email"], "wendel@example.com")

    def test_me_exige_autenticacao(self):
        """Sem token responde 401: dado de perfil nunca fica público."""
        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PasswordChangeTests(APITestCase):
    """POST /api/auth/password/ — troca de senha do usuário logado."""

    def setUp(self):
        self.user = User.objects.create_user(
            "wendel", email="wendel@example.com", password="senha-forte-123"
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_troca_de_senha_com_sucesso(self):
        """Com a senha atual correta, a nova substitui a antiga (204): a nova
        passa a conferir no banco e a antiga deixa de valer."""
        response = self.client.post(
            reverse("password-change"),
            {"old_password": "senha-forte-123", "new_password": "outra-senha-456"},
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("outra-senha-456"))
        self.assertFalse(self.user.check_password("senha-forte-123"))

    def test_token_continua_valido_apos_a_troca(self):
        """Trocar a senha não derruba a sessão: o mesmo token segue
        autenticando as próximas requisições."""
        self.client.post(
            reverse("password-change"),
            {"old_password": "senha-forte-123", "new_password": "outra-senha-456"},
        )
        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_rejeita_senha_atual_errada(self):
        """Senha atual errada responde 400 e a senha antiga permanece
        valendo — ninguém troca senha alheia só com o token."""
        response = self.client.post(
            reverse("password-change"),
            {"old_password": "senha-errada", "new_password": "outra-senha-456"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("senha-forte-123"))

    def test_rejeita_senha_nova_fraca(self):
        """A nova senha passa pelos mesmos validadores do registro:
        fraca → 400."""
        response = self.client.post(
            reverse("password-change"),
            {"old_password": "senha-forte-123", "new_password": "123"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_exige_autenticacao(self):
        """Sem token responde 401: não há troca de senha sem login."""
        self.client.credentials()
        response = self.client.post(
            reverse("password-change"),
            {"old_password": "senha-forte-123", "new_password": "outra-senha-456"},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class LogoutTests(APITestCase):
    """POST /api/auth/logout/ — encerramento da sessão."""

    def setUp(self):
        self.user = User.objects.create_user(
            "wendel", email="wendel@example.com", password="senha-forte-123"
        )
        self.token = Token.objects.create(user=self.user)

    def test_logout_invalida_o_token(self):
        """Logout apaga o token no servidor (204); reusar o mesmo token na
        sequência falha com 401."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        response = self.client.post(reverse("logout"))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Token.objects.filter(user=self.user).exists())

        # O mesmo token não pode ser usado de novo
        response = self.client.post(reverse("logout"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_exige_autenticacao(self):
        """Logout sem token responde 401 (não há sessão para encerrar)."""
        response = self.client.post(reverse("logout"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class LoginThrottleTests(APITestCase):
    """POST /api/auth/login/ — limite de tentativas por IP (anti força bruta)."""

    def setUp(self):
        User.objects.create_user(
            "wendel", email="wendel@example.com", password="senha-forte-123"
        )
        # Em dev (DEBUG=True) o limite fica desligado no settings; o teste
        # força uma taxa baixa para exercitar o comportamento de produção.
        LoginRateThrottle.THROTTLE_RATES = {"login": "3/min"}
        cache.clear()  # zera contagens de requisições de outros testes

    def tearDown(self):
        del LoginRateThrottle.THROTTLE_RATES  # volta à taxa do settings
        cache.clear()

    def test_bloqueia_tentativas_alem_do_limite(self):
        """Estourado o limite, até a senha correta responde 429 — força
        bruta não consegue continuar tentando senhas."""
        for _ in range(3):
            response = self.client.post(
                reverse("login"), {"username": "wendel", "password": "senha-errada"}
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.post(
            reverse("login"), {"username": "wendel", "password": "senha-forte-123"}
        )
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class RegisterThrottleTests(APITestCase):
    """POST /api/auth/register/ — limite de criação de contas por IP."""

    def setUp(self):
        RegisterRateThrottle.THROTTLE_RATES = {"register": "2/hour"}
        cache.clear()

    def tearDown(self):
        del RegisterRateThrottle.THROTTLE_RATES
        cache.clear()

    def test_bloqueia_criacao_de_contas_em_massa(self):
        """Estourado o limite, o registro seguinte responde 429 e nenhuma
        conta extra aparece no banco."""
        for i in range(2):
            response = self.client.post(
                reverse("register"),
                {
                    "username": f"usuario{i}",
                    "email": f"usuario{i}@example.com",
                    "password": "senha-forte-123",
                },
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.post(
            reverse("register"),
            {
                "username": "usuario2",
                "email": "usuario2@example.com",
                "password": "senha-forte-123",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(User.objects.count(), 2)
