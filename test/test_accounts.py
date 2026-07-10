from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase


class RegisterTests(APITestCase):
    def test_registro_cria_usuario_com_senha_hasheada(self):
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
        response = self.client.post(
            reverse("register"),
            {"username": "wendel", "email": "wendel@example.com", "password": "123"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username="wendel").exists())

    def test_registro_rejeita_email_duplicado(self):
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
    def setUp(self):
        self.user = User.objects.create_user(
            "wendel", email="wendel@example.com", password="senha-forte-123"
        )

    def test_login_retorna_token_e_dados_do_usuario(self):
        response = self.client.post(
            reverse("login"), {"username": "wendel", "password": "senha-forte-123"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
        self.assertEqual(response.data["user"]["username"], "wendel")
        self.assertTrue(Token.objects.filter(user=self.user).exists())

    def test_login_rejeita_senha_errada(self):
        response = self.client.post(
            reverse("login"), {"username": "wendel", "password": "senha-errada"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn("token", response.data)


class MeTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            "wendel", email="wendel@example.com", password="senha-forte-123"
        )
        self.token = Token.objects.create(user=self.user)

    def test_me_retorna_nome_e_email_do_usuario_logado(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "wendel")
        self.assertEqual(response.data["email"], "wendel@example.com")

    def test_me_exige_autenticacao(self):
        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PasswordChangeTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            "wendel", email="wendel@example.com", password="senha-forte-123"
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_troca_de_senha_com_sucesso(self):
        response = self.client.post(
            reverse("password-change"),
            {"old_password": "senha-forte-123", "new_password": "outra-senha-456"},
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("outra-senha-456"))
        self.assertFalse(self.user.check_password("senha-forte-123"))

    def test_token_continua_valido_apos_a_troca(self):
        self.client.post(
            reverse("password-change"),
            {"old_password": "senha-forte-123", "new_password": "outra-senha-456"},
        )
        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_rejeita_senha_atual_errada(self):
        response = self.client.post(
            reverse("password-change"),
            {"old_password": "senha-errada", "new_password": "outra-senha-456"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("senha-forte-123"))

    def test_rejeita_senha_nova_fraca(self):
        response = self.client.post(
            reverse("password-change"),
            {"old_password": "senha-forte-123", "new_password": "123"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_exige_autenticacao(self):
        self.client.credentials()
        response = self.client.post(
            reverse("password-change"),
            {"old_password": "senha-forte-123", "new_password": "outra-senha-456"},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class LogoutTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            "wendel", email="wendel@example.com", password="senha-forte-123"
        )
        self.token = Token.objects.create(user=self.user)

    def test_logout_invalida_o_token(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        response = self.client.post(reverse("logout"))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Token.objects.filter(user=self.user).exists())

        # O mesmo token não pode ser usado de novo
        response = self.client.post(reverse("logout"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_exige_autenticacao(self):
        response = self.client.post(reverse("logout"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
