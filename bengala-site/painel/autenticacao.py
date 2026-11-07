from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.decorators import user_passes_test


class EmailBackend(ModelBackend):
    """
    Login do site pelo e-mail do auth_user. Só entra quem é administrador
    (is_staff) e está ativo. A tabela titular não participa: ela é de quem
    usa a bengala, não de quem administra o site.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
        usuario = get_user_model().objects.filter(email__iexact=username, is_staff=True, is_active=True).first()
        if usuario and usuario.check_password(password):
            return usuario
        return None


def admin_required(view):
    """Bloqueia a tela para quem não está logado como administrador."""
    return user_passes_test(lambda u: u.is_active and u.is_staff, login_url="login")(view)
