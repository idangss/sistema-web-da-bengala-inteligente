from decimal import ROUND_HALF_UP, Decimal

from django.utils import timezone
from rest_framework import serializers

from core.models import CONFIRMACOES_SOS, ORIGENS_SOS, TIPOS_DETECCAO, Dispositivo, Titular


class DataHoraLocal(serializers.DateTimeField):
    """
    O banco guarda DATETIME sem fuso, no horário de Manaus. Se o app mandar
    a data com fuso (ex.: 2026-11-07T10:00:00-04:00 ou ...Z), ela é convertida
    para o horário local antes de gravar.
    """

    def enforce_timezone(self, value):
        if timezone.is_aware(value):
            return timezone.make_naive(value, timezone.get_default_timezone())
        return value


class DecimalArredondado(serializers.DecimalField):
    """
    O GPS do celular manda coordenadas com 15 casas decimais e o banco guarda 7.
    O DRF normalmente recusaria; aqui o valor é arredondado antes da checagem.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("rounding", ROUND_HALF_UP)
        kwargs.setdefault("required", False)
        kwargs.setdefault("allow_null", True)
        super().__init__(**kwargs)

    def validate_precision(self, value):
        value = value.quantize(Decimal(1).scaleb(-self.decimal_places), rounding=self.rounding)
        return super().validate_precision(value)


def latitude():
    return DecimalArredondado(max_digits=10, decimal_places=7, min_value=Decimal(-90), max_value=Decimal(90))


def longitude():
    return DecimalArredondado(max_digits=10, decimal_places=7, min_value=Decimal(-180), max_value=Decimal(180))


def conferir_coordenadas(dados):
    # Mesma regra do CHECK ck_*_coord do schema: as duas juntas ou nenhuma.
    if (dados.get("latitude") is None) != (dados.get("longitude") is None):
        raise serializers.ValidationError("Envie latitude e longitude juntas, ou nenhuma das duas.")
    return dados


class AbrirSessaoSerializer(serializers.Serializer):
    dispositivo_id = serializers.IntegerField()
    titular_id = serializers.IntegerField(required=False)
    inicio = DataHoraLocal(required=False)

    def validate(self, dados):
        dispositivo = Dispositivo.objects.filter(pk=dados["dispositivo_id"], excluido_em__isnull=True).first()
        if dispositivo is None:
            raise serializers.ValidationError({"dispositivo_id": "Bengala não encontrada ou desativada."})
        vinculo = dispositivo.vinculos.filter(data_fim__isnull=True).select_related("titular").first()
        if vinculo is None:
            raise serializers.ValidationError({"dispositivo_id": "Esta bengala não está vinculada a nenhum titular."})
        if "titular_id" in dados and dados["titular_id"] != vinculo.titular_id:
            raise serializers.ValidationError({"titular_id": "O titular informado não é o dono atual da bengala."})
        if not vinculo.titular.ativo:
            raise serializers.ValidationError({"titular_id": "O titular desta bengala está desativado."})
        dados["dispositivo"] = dispositivo
        dados["vinculo"] = vinculo
        dados.setdefault("inicio", timezone.now())
        return dados


class EncerrarSessaoSerializer(serializers.Serializer):
    fim = DataHoraLocal(required=False)
    distancia_m = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal(0), required=False, allow_null=True)


class EventoSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=TIPOS_DETECCAO)
    nivel_alerta = serializers.IntegerField(min_value=1, max_value=3)
    distancia_cm = DecimalArredondado(max_digits=6, decimal_places=2, min_value=Decimal(0))
    latitude = latitude()
    longitude = longitude()
    ocorrido_em = DataHoraLocal()

    def validate(self, dados):
        return conferir_coordenadas(dados)


class SosSerializer(serializers.Serializer):
    sessao_id = serializers.IntegerField()
    origem = serializers.ChoiceField(choices=ORIGENS_SOS)
    confirmado_por = serializers.ChoiceField(choices=CONFIRMACOES_SOS, required=False, allow_null=True)
    latitude = latitude()
    longitude = longitude()
    disparado_em = DataHoraLocal(required=False)

    def validate(self, dados):
        return conferir_coordenadas(dados)


class AtualizarSosSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[("CANCELADO", "Cancelado"), ("ATENDIDO", "Atendido")])
    cancelado_em = DataHoraLocal(required=False)


class TelemetriaSerializer(serializers.Serializer):
    dispositivo_id = serializers.IntegerField()
    bateria_pct = serializers.IntegerField(min_value=0, max_value=100)
    rssi_ble = serializers.IntegerField(min_value=-32768, max_value=32767, required=False, allow_null=True)
    registrado_em = DataHoraLocal(required=False)

    def validate_dispositivo_id(self, valor):
        if not Dispositivo.objects.filter(pk=valor, excluido_em__isnull=True).exists():
            raise serializers.ValidationError("Bengala não encontrada ou desativada.")
        return valor


def guarda_localizacao(titular: Titular):
    """LGPD: sem consentimento, as coordenadas são descartadas antes de gravar."""
    return titular.consentimento_localizacao
