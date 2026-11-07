from django.urls import path

from . import views

# Rotas sem barra no final, como o app chama (base terminando em /api/).
urlpatterns = [
    path("sessoes", views.abrir_sessao),
    path("sessoes/<int:sessao_id>", views.encerrar_sessao),
    path("sessoes/<int:sessao_id>/eventos", views.receber_eventos),
    path("sos", views.registrar_sos),
    path("sos/<int:alerta_id>", views.atualizar_sos),
    path("telemetria", views.registrar_telemetria),
    path("mapa/buracos", views.mapa_buracos),
]
