from django import template

from core.consultas import ROTULOS_EVENTO

register = template.Library()


@register.filter
def rotulo_evento(codigo):
    return ROTULOS_EVENTO.get(codigo, codigo)


@register.filter
def duracao(sessao):
    """Duração da sessão em "1 h 30 min"; vazio enquanto ela está aberta."""
    if not sessao.fim:
        return ""
    minutos = int((sessao.fim - sessao.inicio).total_seconds() // 60)
    horas, resto = divmod(minutos, 60)
    return f"{horas} h {resto} min" if horas else f"{resto} min"


@register.filter
def coordenada(valor):
    return f"{float(valor):.5f}" if valor is not None else ""


NIVEIS = {1: "Leve", 2: "Médio", 3: "Crítico"}


@register.filter
def nivel(valor):
    return NIVEIS.get(valor, "")
