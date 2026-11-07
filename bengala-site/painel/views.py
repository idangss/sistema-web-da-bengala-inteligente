from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.contrib.auth.views import LoginView
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, OuterRef, Q, Subquery
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core import consultas
from core.models import (
    AlertaSos, Configuracao, Dispositivo, EventoDeteccao, Sessao, Telemetria,
    Titular, VinculoDispositivo,
)

from .autenticacao import admin_required
from .forms import FormDispositivo, FormFiltroEventos, FormLogin, FormTitular, FormTitularNovo, FormVinculo

POR_PAGINA = 20


class Entrar(LoginView):
    template_name = "registration/login.html"
    form_class = FormLogin
    redirect_authenticated_user = True

    def form_valid(self, form):
        resposta = super().form_valid(form)
        # Sem "manter conectado", a sessão acaba quando o navegador fecha.
        if not form.cleaned_data.get("manter_conectado"):
            self.request.session.set_expiry(0)
        return resposta


def paginar(request, queryset):
    return Paginator(queryset, POR_PAGINA).get_page(request.GET.get("pagina"))


# ---------------------------------------------------------------- Painel

@admin_required
def painel(request):
    bengalas = consultas.bengalas_com_status(Dispositivo.objects.filter(excluido_em__isnull=True)).order_by("numero_serie")
    por_dia = consultas.deteccoes_por_dia(7)
    contadores = {
        "titulares": consultas.titulares_ativos().count(),
        "bengalas": bengalas.count(),
        "conectadas": sum(1 for b in bengalas if b.conectada),
        "deteccoes_7_dias": sum(d["total"] for d in por_dia),
        "sos_abertos": AlertaSos.objects.filter(status="DISPARADO").count(),
    }
    # Os dados dos gráficos e do mapa vão para o HTML via json_script, nunca fixos.
    grafico = {
        "rotulos": [d["dia"].strftime("%d/%m") for d in por_dia],
        "valores": [d["total"] for d in por_dia],
    }
    localizacao = consultas.ultima_localizacao()
    mapa = None
    if localizacao:
        mapa = {k: localizacao[k] for k in ("lat", "lng", "titular", "bengala", "origem")}
        mapa["quando"] = localizacao["quando"].strftime("%d/%m/%Y %H:%M")
    return render(request, "painel/painel.html", {
        "secao": "painel",
        "contadores": contadores,
        "por_dia": por_dia,
        "grafico": grafico,
        "localizacao": localizacao,
        "mapa": mapa,
        "buracos": consultas.buracos_agregados(),
        "bengalas": bengalas,
        "ultimos_eventos": consultas.eventos_unificados()[:8],
        "minutos_conectada": consultas.MINUTOS_CONECTADA,
    })


# ---------------------------------------------------------------- Usuários (tabela titular)

@admin_required
def usuarios(request):
    busca = request.GET.get("q", "").strip()
    status = request.GET.get("status", "ativos")
    bengala_atual = VinculoDispositivo.objects.filter(titular=OuterRef("pk"), data_fim__isnull=True)
    qs = Titular.objects.annotate(
        bengala_serie=Subquery(bengala_atual.values("dispositivo__numero_serie")[:1]),
        bengala_id=Subquery(bengala_atual.values("dispositivo_id")[:1]),
    )
    if busca:
        qs = qs.filter(Q(nome__icontains=busca) | Q(email__icontains=busca) | Q(telefone__icontains=busca))
    if status == "ativos":
        qs = qs.filter(excluido_em__isnull=True)
    elif status == "desativados":
        qs = qs.filter(excluido_em__isnull=False)
    return render(request, "painel/usuarios/lista.html", {
        "secao": "usuarios",
        "pagina": paginar(request, qs.order_by("nome", "id")),
        "busca": busca,
        "status": status,
    })


@admin_required
def usuario_detalhe(request, pk):
    titular = get_object_or_404(Titular, pk=pk)
    return render(request, "painel/usuarios/detalhe.html", {
        "secao": "usuarios",
        "titular": titular,
        "contatos": titular.contatos.filter(excluido_em__isnull=True).order_by("prioridade", "nome"),
        "vinculos": titular.vinculos.select_related("dispositivo").order_by("-data_inicio"),
        "sessoes": titular.sessoes.select_related("dispositivo")
        .annotate(n_eventos=Count("eventos", distinct=True), n_sos=Count("alertas", distinct=True))
        .order_by("-inicio")[:10],
        "alertas": titular.alertas.order_by("-disparado_em")[:10],
    })


@admin_required
def usuario_novo(request):
    form = FormTitularNovo(request.POST or None)
    if request.method == "POST" and form.is_valid():
        titular = form.save(commit=False)
        titular.senha_hash = make_password(form.cleaned_data["senha"])
        titular.save()
        messages.success(request, f"Usuário {titular.nome} cadastrado.")
        return redirect("usuario_detalhe", pk=titular.pk)
    return render(request, "painel/usuarios/form.html", {"secao": "usuarios", "form": form, "titulo": "Cadastrar usuário"})


@admin_required
def usuario_editar(request, pk):
    titular = get_object_or_404(Titular, pk=pk)
    form = FormTitular(request.POST or None, instance=titular)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Dados do usuário atualizados.")
        return redirect("usuario_detalhe", pk=titular.pk)
    return render(request, "painel/usuarios/form.html", {
        "secao": "usuarios", "form": form, "titulo": f"Editar {titular.nome}", "titular": titular,
    })


@admin_required
@require_POST
def usuario_status(request, pk):
    # Exclusão lógica: o schema não permite DELETE, só preencher excluido_em.
    titular = get_object_or_404(Titular, pk=pk)
    if request.POST.get("acao") == "desativar" and titular.ativo:
        titular.excluido_em = timezone.now()
        titular.save(update_fields=["excluido_em"])
        messages.success(request, f"{titular.nome} foi desativado. O histórico continua guardado.")
    elif request.POST.get("acao") == "reativar" and not titular.ativo:
        titular.excluido_em = None
        titular.save(update_fields=["excluido_em"])
        messages.success(request, f"{titular.nome} foi reativado.")
    return redirect("usuario_detalhe", pk=titular.pk)


# ---------------------------------------------------------------- Bengalas (tabela dispositivo)

@admin_required
def bengalas(request):
    busca = request.GET.get("q", "").strip()
    status = request.GET.get("status", "ativas")
    qs = consultas.bengalas_com_status()
    if busca:
        qs = qs.filter(Q(numero_serie__icontains=busca) | Q(mac_ble__icontains=busca))
    if status == "ativas":
        qs = qs.filter(excluido_em__isnull=True)
    elif status == "desativadas":
        qs = qs.filter(excluido_em__isnull=False)
    return render(request, "painel/bengalas/lista.html", {
        "secao": "bengalas",
        "pagina": paginar(request, qs.order_by("numero_serie")),
        "busca": busca,
        "status": status,
        "minutos_conectada": consultas.MINUTOS_CONECTADA,
    })


@admin_required
def bengala_detalhe(request, pk):
    bengala = get_object_or_404(consultas.bengalas_com_status(), pk=pk)
    sessoes = (
        bengala.sessoes.select_related("titular")
        .annotate(n_eventos=Count("eventos", distinct=True), n_sos=Count("alertas", distinct=True))
        .order_by("-inicio")
    )
    return render(request, "painel/bengalas/detalhe.html", {
        "secao": "bengalas",
        "bengala": bengala,
        "configuracao": Configuracao.objects.filter(dispositivo=bengala).first(),
        "vinculos": bengala.vinculos.select_related("titular").order_by("-data_inicio"),
        "pagina": paginar(request, sessoes),
        "form_vinculo": FormVinculo(),
        "sessao_aberta": bengala.sessoes.filter(fim__isnull=True).exists(),
        "minutos_conectada": consultas.MINUTOS_CONECTADA,
    })


@admin_required
def bengala_nova(request):
    form = FormDispositivo(request.POST or None)
    if request.method == "POST" and form.is_valid():
        # A bengala nasce com a configuração padrão (os mesmos DEFAULT do schema).
        with transaction.atomic():
            bengala = form.save()
            Configuracao.objects.create(dispositivo=bengala)
        messages.success(request, f"Bengala {bengala.numero_serie} cadastrada.")
        return redirect("bengala_detalhe", pk=bengala.pk)
    return render(request, "painel/bengalas/form.html", {"secao": "bengalas", "form": form, "titulo": "Cadastrar bengala"})


@admin_required
def bengala_editar(request, pk):
    bengala = get_object_or_404(Dispositivo, pk=pk)
    form = FormDispositivo(request.POST or None, instance=bengala)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Dados da bengala atualizados.")
        return redirect("bengala_detalhe", pk=bengala.pk)
    return render(request, "painel/bengalas/form.html", {
        "secao": "bengalas", "form": form, "titulo": f"Editar bengala {bengala.numero_serie}", "bengala": bengala,
    })


@admin_required
@require_POST
def bengala_vinculo(request, pk):
    """
    Troca o dono da bengala. O vínculo antigo não é apagado: recebe data_fim,
    para o histórico continuar dizendo quem usava a bengala em cada sessão.
    """
    bengala = get_object_or_404(Dispositivo, pk=pk)
    if bengala.sessoes.filter(fim__isnull=True).exists():
        messages.error(request, "Há uma sessão de uso em andamento. Ela precisa terminar antes de trocar o titular.")
        return redirect("bengala_detalhe", pk=pk)
    atual = bengala.vinculos.filter(data_fim__isnull=True).first()
    agora = timezone.now()

    if request.POST.get("acao") == "desvincular":
        if atual:
            atual.data_fim = agora
            atual.save(update_fields=["data_fim"])
            messages.success(request, "Bengala desvinculada do titular.")
        return redirect("bengala_detalhe", pk=pk)

    form = FormVinculo(request.POST)
    if not form.is_valid():
        messages.error(request, "Escolha um titular ativo para vincular.")
        return redirect("bengala_detalhe", pk=pk)
    novo = form.cleaned_data["titular"]
    if atual and atual.titular_id == novo.pk:
        messages.info(request, f"A bengala já está com {novo.nome}.")
        return redirect("bengala_detalhe", pk=pk)

    with transaction.atomic():
        if atual:
            atual.data_fim = agora
            atual.save(update_fields=["data_fim"])
        VinculoDispositivo.objects.create(titular=novo, dispositivo=bengala, data_inicio=agora)
        if bengala.data_ativacao is None:
            bengala.data_ativacao = agora
            bengala.save(update_fields=["data_ativacao"])
    messages.success(request, f"Bengala vinculada a {novo.nome}.")
    return redirect("bengala_detalhe", pk=pk)


@admin_required
@require_POST
def bengala_status(request, pk):
    bengala = get_object_or_404(Dispositivo, pk=pk)
    if request.POST.get("acao") == "desativar" and bengala.ativo:
        bengala.excluido_em = timezone.now()
        bengala.save(update_fields=["excluido_em"])
        messages.success(request, f"Bengala {bengala.numero_serie} desativada. O histórico continua guardado.")
    elif request.POST.get("acao") == "reativar" and not bengala.ativo:
        bengala.excluido_em = None
        bengala.save(update_fields=["excluido_em"])
        messages.success(request, f"Bengala {bengala.numero_serie} reativada.")
    return redirect("bengala_detalhe", pk=pk)


# ---------------------------------------------------------------- Sensores

@admin_required
def sensores(request):
    lista = Dispositivo.objects.filter(excluido_em__isnull=True).order_by("numero_serie")
    escolhida = lista.filter(pk=request.GET.get("bengala")).first() if request.GET.get("bengala", "").isdigit() else None
    escolhida = escolhida or lista.first()
    contexto = {"secao": "sensores", "lista": lista, "bengala": None}
    if escolhida is None:
        return render(request, "painel/sensores.html", contexto)

    bengala = consultas.bengalas_com_status().get(pk=escolhida.pk)
    leituras = list(Telemetria.objects.filter(dispositivo=bengala).order_by("-registrado_em", "-id")[:50])
    leituras.reverse()
    deteccoes = EventoDeteccao.objects.filter(sessao__dispositivo=bengala).order_by("-ocorrido_em")
    alertas = AlertaSos.objects.filter(sessao__dispositivo=bengala).order_by("-disparado_em")

    # O banco não grava leituras brutas nem o estado de cada sensor (ajuste
    # pendente). Mostramos o que existe: a última detecção de cada sensor.
    contexto.update({
        "bengala": bengala,
        "configuracao": Configuracao.objects.filter(dispositivo=bengala).first(),
        "leituras": leituras,
        "grafico": {
            "rotulos": [t.registrado_em.strftime("%d/%m %H:%M") for t in leituras],
            "bateria": [t.bateria_pct for t in leituras],
            "rssi": [t.rssi_ble for t in leituras],
        },
        "sensores": [
            {
                "nome": "Sensor frontal",
                "funcao": "Obstáculos à frente",
                "ultimo": deteccoes.filter(tipo="OBSTACULO").first(),
            },
            {
                "nome": "Sensor inferior (laser VL53L1X)",
                "funcao": "Buracos e degraus",
                "ultimo": deteccoes.filter(tipo__in=["BURACO", "DEGRAU_SUBIDA", "DEGRAU_DESCIDA"]).first(),
            },
        ],
        "ultima_queda": alertas.filter(origem="QUEDA").first(),
        "ultimo_botao": alertas.filter(origem="BOTAO").first(),
        "minutos_conectada": consultas.MINUTOS_CONECTADA,
    })
    return render(request, "painel/sensores.html", contexto)


# ---------------------------------------------------------------- Eventos

@admin_required
def eventos(request):
    form = FormFiltroEventos(request.GET or None)
    filtros = {}
    if form.is_bound and form.is_valid():
        dados = form.cleaned_data
        filtros = {
            "inicio": dados["inicio"],
            "fim": dados["fim"],
            "titular_id": dados["titular"].pk if dados["titular"] else None,
            "dispositivo_id": dados["bengala"].pk if dados["bengala"] else None,
            "tipo": dados["tipo"] or None,
        }
    return render(request, "painel/eventos.html", {
        "secao": "eventos",
        "form": form,
        "pagina": paginar(request, consultas.eventos_unificados(**filtros)),
        "bateria_baixa": consultas.BATERIA_BAIXA_PCT,
    })


@admin_required
def sessao_detalhe(request, pk):
    sessao = get_object_or_404(Sessao.objects.select_related("titular", "dispositivo"), pk=pk)
    return render(request, "painel/sessao.html", {
        "secao": "bengalas",
        "sessao": sessao,
        "deteccoes": sessao.eventos.order_by("ocorrido_em"),
        "alertas": sessao.alertas.prefetch_related("notificacoes__contato").order_by("disparado_em"),
        "trajetos": sessao.trajetos.annotate(n_pontos=Count("pontos")).order_by("iniciado_em"),
    })
