# Consultas usadas por mais de uma tela (e pela API). Tudo pelo ORM.

from datetime import timedelta

from django.db.models import (
    BooleanField, Case, CharField, Count, DecimalField, F,
    IntegerField, OuterRef, Q, Subquery, Value, When,
)
from django.db.models.functions import Round, TruncDate
from django.utils import timezone

from .models import (
    TIPOS_DETECCAO, AlertaSos, Dispositivo, EventoDeteccao, Telemetria,
    Titular, VinculoDispositivo,
)

# Bengala "conectada" = mandou telemetria há menos de 5 minutos (sugestão do PDF).
MINUTOS_CONECTADA = 5
# Telemetria com bateria até este valor aparece como evento "Bateria baixa".
BATERIA_BAIXA_PCT = 15

ROTULOS_EVENTO = dict(TIPOS_DETECCAO) | {
    "QUEDA": "Queda (S.O.S.)",
    "BOTAO": "Botão S.O.S.",
    "BATERIA_BAIXA": "Bateria baixa",
}


def limite_conexao():
    return timezone.now() - timedelta(minutes=MINUTOS_CONECTADA)


def bengalas_com_status(dispositivos=None):
    """Acrescenta a cada bengala a última telemetria, se está conectada e o titular atual."""
    if dispositivos is None:
        dispositivos = Dispositivo.objects.all()
    ultima = Telemetria.objects.filter(dispositivo=OuterRef("pk")).order_by("-registrado_em", "-id")
    vinculo = VinculoDispositivo.objects.filter(dispositivo=OuterRef("pk"), data_fim__isnull=True)
    return dispositivos.annotate(
        ultima_comunicacao=Subquery(ultima.values("registrado_em")[:1]),
        bateria=Subquery(ultima.values("bateria_pct")[:1]),
        rssi=Subquery(ultima.values("rssi_ble")[:1]),
        titular_atual_id=Subquery(vinculo.values("titular_id")[:1]),
        titular_atual_nome=Subquery(vinculo.values("titular__nome")[:1]),
    ).annotate(
        conectada=Case(
            When(ultima_comunicacao__gte=limite_conexao(), then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )
    )


# Colunas comuns das três fontes de eventos. Os nomes começam com "ev_" para
# não colidir com os nomes das colunas das tabelas.
COLUNAS_EVENTO = [
    "ev_fonte", "ev_id", "ev_tipo", "ev_quando", "ev_titular_id", "ev_titular_nome",
    "ev_consentimento", "ev_dispositivo_id", "ev_serie", "ev_distancia", "ev_nivel",
    "ev_bateria", "ev_status", "ev_lat", "ev_lng",
]


def _nulo(campo):
    return Value(None, output_field=campo)


def eventos_unificados(inicio=None, fim=None, titular_id=None, dispositivo_id=None, tipo=None):
    """
    Histórico único de eventos, juntando três tabelas com UNION ALL no banco:
      - evento_deteccao (obstáculo, buraco, degraus)
      - alerta_sos (queda e botão)
      - telemetria com bateria baixa
    Resolve o ajuste pendente "tipos de evento" sem criar view nem alterar
    o schema. Devolve um queryset ordenado do mais novo para o mais antigo,
    pronto para paginar no servidor.
    """
    texto, inteiro, decimal = CharField(), IntegerField(), DecimalField(max_digits=10, decimal_places=7)

    deteccoes = EventoDeteccao.objects.annotate(
        ev_fonte=Value("DETECCAO", output_field=texto),
        ev_id=F("id"),
        ev_tipo=F("tipo"),
        ev_quando=F("ocorrido_em"),
        ev_titular_id=F("sessao__titular_id"),
        ev_titular_nome=F("sessao__titular__nome"),
        ev_consentimento=F("sessao__titular__consentimento_localizacao"),
        ev_dispositivo_id=F("sessao__dispositivo_id"),
        ev_serie=F("sessao__dispositivo__numero_serie"),
        ev_distancia=F("distancia_cm"),
        ev_nivel=F("nivel_alerta"),
        ev_bateria=_nulo(inteiro),
        ev_status=_nulo(texto),
        ev_lat=F("latitude"),
        ev_lng=F("longitude"),
    )

    alertas = AlertaSos.objects.annotate(
        ev_fonte=Value("SOS", output_field=texto),
        ev_id=F("id"),
        ev_tipo=F("origem"),
        ev_quando=F("disparado_em"),
        ev_titular_id=F("titular_id"),
        ev_titular_nome=F("titular__nome"),
        ev_consentimento=F("titular__consentimento_localizacao"),
        ev_dispositivo_id=F("sessao__dispositivo_id"),
        ev_serie=F("sessao__dispositivo__numero_serie"),
        ev_distancia=_nulo(DecimalField(max_digits=6, decimal_places=2)),
        ev_nivel=_nulo(inteiro),
        ev_bateria=_nulo(inteiro),
        ev_status=F("status"),
        ev_lat=F("latitude"),
        ev_lng=F("longitude"),
    )

    # A telemetria não tem sessão: o titular é o do vínculo válido na hora da leitura.
    vinculo_na_hora = VinculoDispositivo.objects.filter(
        dispositivo=OuterRef("dispositivo_id"), data_inicio__lte=OuterRef("registrado_em")
    ).filter(Q(data_fim__isnull=True) | Q(data_fim__gte=OuterRef("registrado_em"))).order_by("-data_inicio")
    baterias = Telemetria.objects.filter(bateria_pct__lte=BATERIA_BAIXA_PCT).annotate(
        ev_fonte=Value("BATERIA", output_field=texto),
        ev_id=F("id"),
        ev_tipo=Value("BATERIA_BAIXA", output_field=texto),
        ev_quando=F("registrado_em"),
        ev_titular_id=Subquery(vinculo_na_hora.values("titular_id")[:1], output_field=inteiro),
        ev_titular_nome=Subquery(vinculo_na_hora.values("titular__nome")[:1], output_field=texto),
        ev_consentimento=Value(False, output_field=BooleanField()),
        ev_dispositivo_id=F("dispositivo_id"),
        ev_serie=F("dispositivo__numero_serie"),
        ev_distancia=_nulo(DecimalField(max_digits=6, decimal_places=2)),
        ev_nivel=_nulo(inteiro),
        ev_bateria=F("bateria_pct"),
        ev_status=_nulo(texto),
        ev_lat=_nulo(decimal),
        ev_lng=_nulo(decimal),
    )

    fontes = []
    tipos_deteccao = dict(TIPOS_DETECCAO)
    if tipo is None or tipo in tipos_deteccao:
        fontes.append(deteccoes.filter(tipo=tipo) if tipo else deteccoes)
    if tipo is None or tipo in ("QUEDA", "BOTAO"):
        fontes.append(alertas.filter(origem=tipo) if tipo else alertas)
    if tipo is None or tipo == "BATERIA_BAIXA":
        fontes.append(baterias)

    filtradas = []
    for qs in fontes:
        if inicio:
            qs = qs.filter(ev_quando__date__gte=inicio)
        if fim:
            qs = qs.filter(ev_quando__date__lte=fim)
        if titular_id:
            qs = qs.filter(ev_titular_id=titular_id)
        if dispositivo_id:
            qs = qs.filter(ev_dispositivo_id=dispositivo_id)
        filtradas.append(qs.values(*COLUNAS_EVENTO))

    if not filtradas:
        return EventoDeteccao.objects.none().values(*COLUNAS_EVENTO)
    resultado = filtradas[0]
    if len(filtradas) > 1:
        resultado = resultado.union(*filtradas[1:], all=True)
    return resultado.order_by("-ev_quando", "-ev_id")


def ultima_localizacao():
    """
    Posição mais recente gravada (detecção ou S.O.S.), só de titulares que
    deram consentimento de localização (LGPD).
    """
    candidatos = []
    evento = (
        EventoDeteccao.objects.filter(latitude__isnull=False, sessao__titular__consentimento_localizacao=True)
        .select_related("sessao__titular", "sessao__dispositivo")
        .order_by("-ocorrido_em").first()
    )
    if evento:
        candidatos.append({
            "lat": float(evento.latitude), "lng": float(evento.longitude),
            "quando": evento.ocorrido_em, "titular": evento.sessao.titular.nome,
            "bengala": evento.sessao.dispositivo.numero_serie,
            "origem": ROTULOS_EVENTO.get(evento.tipo, evento.tipo),
        })
    alerta = (
        AlertaSos.objects.filter(latitude__isnull=False, titular__consentimento_localizacao=True)
        .select_related("titular", "sessao__dispositivo")
        .order_by("-disparado_em").first()
    )
    if alerta:
        candidatos.append({
            "lat": float(alerta.latitude), "lng": float(alerta.longitude),
            "quando": alerta.disparado_em, "titular": alerta.titular.nome,
            "bengala": alerta.sessao.dispositivo.numero_serie,
            "origem": ROTULOS_EVENTO.get(alerta.origem, alerta.origem),
        })
    if not candidatos:
        return None
    return max(candidatos, key=lambda c: c["quando"])


def deteccoes_por_dia(dias=7):
    """Quantidade de detecções (evento_deteccao) por dia, incluindo dias sem nenhuma."""
    hoje = timezone.now().date()
    primeiro = hoje - timedelta(days=dias - 1)
    linhas = (
        EventoDeteccao.objects.filter(ocorrido_em__date__gte=primeiro)
        .annotate(dia=TruncDate("ocorrido_em"))
        .values("dia")
        .annotate(total=Count("id"))
    )
    por_dia = {linha["dia"]: linha["total"] for linha in linhas}
    resultado = []
    for i in range(dias):
        dia = primeiro + timedelta(days=i)
        resultado.append({"dia": dia, "total": por_dia.get(dia, 0)})
    return resultado


def buracos_agregados(minimo=3):
    """
    Mapa colaborativo: buracos agrupados por coordenada arredondada (4 casas,
    cerca de 11 m). Mostra só pontos com pelo menos `minimo` ocorrências e só
    de titulares com consentimento. Nunca devolve trajeto de ninguém.
    """
    linhas = (
        EventoDeteccao.objects.filter(
            tipo="BURACO", latitude__isnull=False, sessao__titular__consentimento_localizacao=True
        )
        .annotate(lat=Round("latitude", 4), lng=Round("longitude", 4))
        .values("lat", "lng")
        .annotate(ocorrencias=Count("id"))
        .filter(ocorrencias__gte=minimo)
        .order_by("-ocorrencias")
    )
    return [{"lat": float(l["lat"]), "lng": float(l["lng"]), "ocorrencias": l["ocorrencias"]} for l in linhas]


def titulares_ativos():
    return Titular.objects.filter(excluido_em__isnull=True)
