from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.consultas import buracos_agregados
from core.models import AlertaSos, EventoDeteccao, Sessao, Telemetria

from .serializers import (
    AbrirSessaoSerializer, AtualizarSosSerializer, EncerrarSessaoSerializer,
    EventoSerializer, SosSerializer, TelemetriaSerializer, guarda_localizacao,
)

MAX_EVENTOS_POR_LOTE = 1000


@api_view(["POST"])
def abrir_sessao(request):
    entrada = AbrirSessaoSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)
    dados = entrada.validated_data
    vinculo = dados["vinculo"]

    # O schema só aceita uma sessão aberta por bengala (uq_sessao_aberta).
    aberta = Sessao.objects.filter(dispositivo=dados["dispositivo"], fim__isnull=True).first()
    if aberta:
        return Response(
            {"detail": "Esta bengala já tem uma sessão aberta. Encerre-a antes de abrir outra.", "sessao_aberta_id": aberta.pk},
            status=status.HTTP_409_CONFLICT,
        )
    sessao = Sessao.objects.create(
        vinculo=vinculo, titular_id=vinculo.titular_id, dispositivo=dados["dispositivo"], inicio=dados["inicio"]
    )
    return Response(
        {"id": sessao.pk, "titular_id": sessao.titular_id, "dispositivo_id": sessao.dispositivo_id},
        status=status.HTTP_201_CREATED,
    )


@api_view(["PATCH"])
def encerrar_sessao(request, sessao_id):
    sessao = get_object_or_404(Sessao, pk=sessao_id)
    if sessao.fim is not None:
        return Response({"detail": "Esta sessão já foi encerrada."}, status=status.HTTP_409_CONFLICT)
    entrada = EncerrarSessaoSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)
    fim = entrada.validated_data.get("fim") or timezone.now()
    if fim < sessao.inicio:
        return Response({"fim": ["O fim não pode ser antes do início da sessão."]}, status=status.HTTP_400_BAD_REQUEST)
    sessao.fim = fim
    if "distancia_m" in entrada.validated_data:
        sessao.distancia_m = entrada.validated_data["distancia_m"]
    sessao.save(update_fields=["fim", "distancia_m"])
    return Response({"id": sessao.pk, "fim": sessao.fim})


@api_view(["POST"])
def receber_eventos(request, sessao_id):
    """
    Recebe um LOTE de detecções e grava tudo numa única transação: ou entram
    todas, ou nenhuma. A resposta 201 só sai depois de gravar; é ela que o
    app usa para marcar os eventos da fila local como sincronizados.
    Aceita uma lista [...] ou um objeto {"eventos": [...]}.
    """
    sessao = get_object_or_404(Sessao.objects.select_related("titular"), pk=sessao_id)
    lista = request.data.get("eventos", []) if isinstance(request.data, dict) else request.data
    entrada = EventoSerializer(data=lista, many=True, allow_empty=False, max_length=MAX_EVENTOS_POR_LOTE)
    entrada.is_valid(raise_exception=True)

    com_local = guarda_localizacao(sessao.titular)
    novos = []
    for e in entrada.validated_data:
        if not com_local:
            e["latitude"] = None
            e["longitude"] = None
        novos.append(EventoDeteccao(sessao=sessao, **e))
    with transaction.atomic():
        EventoDeteccao.objects.bulk_create(novos)
    return Response({"sessao_id": sessao.pk, "gravados": len(novos)}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def registrar_sos(request):
    """
    Só registra o histórico. O aviso aos contatos sai direto do celular:
    o socorro nunca pode depender do servidor estar no ar.
    """
    entrada = SosSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)
    dados = entrada.validated_data
    sessao = get_object_or_404(Sessao.objects.select_related("titular"), pk=dados["sessao_id"])
    com_local = guarda_localizacao(sessao.titular)
    alerta = AlertaSos.objects.create(
        sessao=sessao,
        titular_id=sessao.titular_id,
        origem=dados["origem"],
        confirmado_por=dados.get("confirmado_por"),
        latitude=dados.get("latitude") if com_local else None,
        longitude=dados.get("longitude") if com_local else None,
        disparado_em=dados.get("disparado_em") or timezone.now(),
    )
    return Response({"id": alerta.pk, "status": alerta.status}, status=status.HTTP_201_CREATED)


@api_view(["PATCH"])
def atualizar_sos(request, alerta_id):
    alerta = get_object_or_404(AlertaSos, pk=alerta_id)
    if alerta.status != "DISPARADO":
        return Response({"detail": f"Este alerta já está {alerta.get_status_display().lower()}."}, status=status.HTTP_409_CONFLICT)
    entrada = AtualizarSosSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)
    alerta.status = entrada.validated_data["status"]
    if alerta.status == "CANCELADO":
        alerta.cancelado_em = entrada.validated_data.get("cancelado_em") or timezone.now()
    alerta.save(update_fields=["status", "cancelado_em"])
    return Response({"id": alerta.pk, "status": alerta.status, "cancelado_em": alerta.cancelado_em})


@api_view(["POST"])
def registrar_telemetria(request):
    entrada = TelemetriaSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)
    dados = entrada.validated_data
    leitura = Telemetria.objects.create(
        dispositivo_id=dados["dispositivo_id"],
        bateria_pct=dados["bateria_pct"],
        rssi_ble=dados.get("rssi_ble"),
        registrado_em=dados.get("registrado_em") or timezone.now(),
    )
    return Response({"id": leitura.pk}, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def mapa_buracos(request):
    """Pontos agregados do mapa colaborativo (nunca o trajeto de uma pessoa)."""
    minimo = request.query_params.get("minimo", "3")
    minimo = int(minimo) if minimo.isdigit() and int(minimo) >= 1 else 3
    return Response({"minimo_ocorrencias": minimo, "pontos": buracos_agregados(minimo)})
