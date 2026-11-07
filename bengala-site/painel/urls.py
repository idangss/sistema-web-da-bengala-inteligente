from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path("entrar/", views.Entrar.as_view(), name="login"),
    path("sair/", LogoutView.as_view(), name="logout"),
    path("", views.painel, name="painel"),
    path("usuarios/", views.usuarios, name="usuarios"),
    path("usuarios/novo/", views.usuario_novo, name="usuario_novo"),
    path("usuarios/<int:pk>/", views.usuario_detalhe, name="usuario_detalhe"),
    path("usuarios/<int:pk>/editar/", views.usuario_editar, name="usuario_editar"),
    path("usuarios/<int:pk>/status/", views.usuario_status, name="usuario_status"),
    path("bengalas/", views.bengalas, name="bengalas"),
    path("bengalas/nova/", views.bengala_nova, name="bengala_nova"),
    path("bengalas/<int:pk>/", views.bengala_detalhe, name="bengala_detalhe"),
    path("bengalas/<int:pk>/editar/", views.bengala_editar, name="bengala_editar"),
    path("bengalas/<int:pk>/vinculo/", views.bengala_vinculo, name="bengala_vinculo"),
    path("bengalas/<int:pk>/status/", views.bengala_status, name="bengala_status"),
    path("sessoes/<int:pk>/", views.sessao_detalhe, name="sessao_detalhe"),
    path("sensores/", views.sensores, name="sensores"),
    path("eventos/", views.eventos, name="eventos"),
]
