# Models das 12 tabelas do schema.sql.
#
# Equivalentes ao que "python manage.py inspectdb" gera, já revisados
# (nomes, ForeignKey, related_name). Diferenças em relação ao inspectdb:
#   - managed = False em todos: o Django usa as tabelas, mas nunca cria nem
#     altera a estrutura delas (quem manda é o schema.sql).
#   - As colunas geradas (dispositivo_vinculado, dispositivo_em_uso) ficaram
#     de fora de propósito: o MariaDB calcula sozinho e recusa INSERT nelas.
#   - O Django não tem chave estrangeira composta. As FKs compostas do schema
#     (sessao -> vinculo, alerta_sos -> sessao, notificacao_sos -> alerta e
#     contato) viraram FKs simples aqui; quem garante a coerência é o banco.
#   - on_delete=PROTECT espelha o ON DELETE RESTRICT: nada é apagado com
#     DELETE, a exclusão é lógica (coluna excluido_em).

from django.db import models
from django.utils import timezone

TIPOS_DETECCAO = [
    ("OBSTACULO", "Obstáculo"),
    ("BURACO", "Buraco"),
    ("DEGRAU_SUBIDA", "Degrau (subida)"),
    ("DEGRAU_DESCIDA", "Degrau (descida)"),
]
ORIGENS_SOS = [("QUEDA", "Queda"), ("BOTAO", "Botão S.O.S.")]
CONFIRMACOES_SOS = [
    ("BENGALA", "Bengala"),
    ("BENGALA_CELULAR", "Bengala e celular"),
    ("CELULAR", "Celular"),
    ("RELOGIO", "Relógio"),
]
STATUS_SOS = [("DISPARADO", "Disparado"), ("CANCELADO", "Cancelado"), ("ATENDIDO", "Atendido")]
CANAIS_NOTIFICACAO = [("SMS", "SMS"), ("WHATSAPP", "WhatsApp"), ("PUSH", "Push"), ("LIGACAO", "Ligação")]
STATUS_ENVIO = [("PENDENTE", "Pendente"), ("ENVIADO", "Enviado"), ("FALHA", "Falha")]
STATUS_TRAJETO = [("EM_ANDAMENTO", "Em andamento"), ("CONCLUIDO", "Concluído"), ("INTERROMPIDO", "Interrompido")]


class Titular(models.Model):
    id = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=120)
    telefone = models.CharField(max_length=20)
    email = models.EmailField(max_length=120, unique=True)
    senha_hash = models.CharField(max_length=255)
    consentimento_localizacao = models.BooleanField(default=False)
    data_cadastro = models.DateTimeField(default=timezone.now)
    excluido_em = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "titular"

    def __str__(self):
        return self.nome

    @property
    def ativo(self):
        return self.excluido_em is None


class ContatoEmergencia(models.Model):
    id = models.AutoField(primary_key=True)
    titular = models.ForeignKey(Titular, models.PROTECT, related_name="contatos")
    nome = models.CharField(max_length=120)
    telefone = models.CharField(max_length=20)
    parentesco = models.CharField(max_length=50, blank=True, null=True)
    prioridade = models.PositiveSmallIntegerField(default=1)
    pode_monitorar = models.BooleanField(default=False)
    excluido_em = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "contato_emergencia"

    def __str__(self):
        return self.nome


class Dispositivo(models.Model):
    id = models.AutoField(primary_key=True)
    mac_ble = models.CharField(max_length=17, unique=True)
    numero_serie = models.CharField(max_length=30, unique=True)
    versao_firmware = models.CharField(max_length=20, blank=True, null=True)
    data_ativacao = models.DateTimeField(blank=True, null=True)
    excluido_em = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "dispositivo"

    def __str__(self):
        return self.numero_serie

    @property
    def ativo(self):
        return self.excluido_em is None


class VinculoDispositivo(models.Model):
    id = models.AutoField(primary_key=True)
    titular = models.ForeignKey(Titular, models.PROTECT, related_name="vinculos")
    dispositivo = models.ForeignKey(Dispositivo, models.PROTECT, related_name="vinculos")
    data_inicio = models.DateTimeField(default=timezone.now)
    data_fim = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "vinculo_dispositivo"


class Configuracao(models.Model):
    dispositivo = models.OneToOneField(Dispositivo, models.PROTECT, primary_key=True, related_name="configuracao")
    altura_sensor_cm = models.DecimalField(max_digits=5, decimal_places=2, default=45)
    angulo_sensor_graus = models.DecimalField(max_digits=5, decimal_places=2, default=40)
    limiar_buraco_cm = models.DecimalField(max_digits=5, decimal_places=2, default=7)
    limiar_frontal_cm = models.IntegerField(default=200)
    intensidade_vibracao = models.PositiveSmallIntegerField(default=80)
    som_ativo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = "configuracao"


class Sessao(models.Model):
    id = models.AutoField(primary_key=True)
    vinculo = models.ForeignKey(VinculoDispositivo, models.PROTECT, related_name="sessoes")
    titular = models.ForeignKey(Titular, models.PROTECT, related_name="sessoes")
    dispositivo = models.ForeignKey(Dispositivo, models.PROTECT, related_name="sessoes")
    inicio = models.DateTimeField()
    fim = models.DateTimeField(blank=True, null=True)
    distancia_m = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "sessao"


class EventoDeteccao(models.Model):
    id = models.BigAutoField(primary_key=True)
    sessao = models.ForeignKey(Sessao, models.PROTECT, related_name="eventos")
    tipo = models.CharField(max_length=20, choices=TIPOS_DETECCAO)
    nivel_alerta = models.PositiveSmallIntegerField()
    distancia_cm = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    ocorrido_em = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "evento_deteccao"


class AlertaSos(models.Model):
    id = models.AutoField(primary_key=True)
    sessao = models.ForeignKey(Sessao, models.PROTECT, related_name="alertas")
    titular = models.ForeignKey(Titular, models.PROTECT, related_name="alertas")
    origem = models.CharField(max_length=15, choices=ORIGENS_SOS)
    confirmado_por = models.CharField(max_length=15, choices=CONFIRMACOES_SOS, blank=True, null=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    disparado_em = models.DateTimeField()
    status = models.CharField(max_length=15, choices=STATUS_SOS, default="DISPARADO")
    cancelado_em = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "alerta_sos"


class NotificacaoSos(models.Model):
    id = models.AutoField(primary_key=True)
    alerta = models.ForeignKey(AlertaSos, models.PROTECT, related_name="notificacoes")
    contato = models.ForeignKey(ContatoEmergencia, models.PROTECT, related_name="notificacoes")
    titular = models.ForeignKey(Titular, models.PROTECT, related_name="notificacoes")
    canal = models.CharField(max_length=15, choices=CANAIS_NOTIFICACAO)
    status_envio = models.CharField(max_length=15, choices=STATUS_ENVIO, default="PENDENTE")
    enviado_em = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "notificacao_sos"


class Trajeto(models.Model):
    id = models.AutoField(primary_key=True)
    sessao = models.ForeignKey(Sessao, models.PROTECT, related_name="trajetos")
    destino_texto = models.CharField(max_length=200)
    destino_lat = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    destino_lng = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    iniciado_em = models.DateTimeField()
    concluido_em = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=15, choices=STATUS_TRAJETO, default="EM_ANDAMENTO")

    class Meta:
        managed = False
        db_table = "trajeto"


class TrajetoPonto(models.Model):
    id = models.BigAutoField(primary_key=True)
    trajeto = models.ForeignKey(Trajeto, models.PROTECT, related_name="pontos")
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    registrado_em = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "trajeto_ponto"


class Telemetria(models.Model):
    id = models.BigAutoField(primary_key=True)
    dispositivo = models.ForeignKey(Dispositivo, models.PROTECT, related_name="telemetrias")
    bateria_pct = models.PositiveSmallIntegerField()
    rssi_ble = models.SmallIntegerField(blank=True, null=True)
    registrado_em = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "telemetria"
