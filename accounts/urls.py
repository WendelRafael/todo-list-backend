"""Rotas de autenticação: /api/auth/register/, /login/ e /logout/."""

from django.urls import path

from .views import (
    LoginView,
    LogoutView,
    MeView,
    PasswordChangeView,
    RegisterView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("password/", PasswordChangeView.as_view(), name="password-change"),
]
