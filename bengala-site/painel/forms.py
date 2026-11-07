import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm

from core.consultas import ROTULOS_EVENTO, titulares_ativos
from core.models import Dispositivo, Titular


class FormBootstrap:
    """Aplica as classes do Bootstrap em todos os campos."""

    def aplicar_estilo(self):
        for campo in self.fields.values():
            if isinstance(campo.widget, forms.CheckboxInput):
                campo.widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(campo.widget, forms.Select):
                campo.widget.attrs.setdefault("class", "form-select")
            else:
                campo.widget.attrs.setdefault("class", "form-control")


class FormLogin(FormBootstrap, AuthenticationForm):
    username = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True}),
    )
    manter_conectado = forms.BooleanField(label="Manter conectado", required=False)

    error_messages = {
        "invalid_login": "E-mail ou senha incorretos. Somente administradores podem entrar.",
        "inactive": "Esta conta está desativada.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilo()


class FormTitular(FormBootstrap, forms.ModelForm):
    class Meta:
        model = Titular
        fields = ["nome", "telefone", "email", "consentimento_localizacao"]
        labels = {
            "nome": "Nome completo",
            "telefone": "Telefone",
            "email": "E-mail",
            "consentimento_localizacao": "Autoriza o registro e a exibição da localização (LGPD)",
        }
        widgets = {"telefone": forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilo()


class FormTitularNovo(FormTitular):
    # A senha é a do app do celular. Só o hash é gravado em titular.senha_hash.
    senha = forms.CharField(
        label="Senha inicial do app", min_length=8,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Mínimo de 8 caracteres. A senha nunca é mostrada nem gravada em texto.",
    )
    confirmar_senha = forms.CharField(
        label="Confirmar senha", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilo()

    def clean(self):
        dados = super().clean()
        if dados.get("senha") and dados.get("senha") != dados.get("confirmar_senha"):
            self.add_error("confirmar_senha", "As senhas não são iguais.")
        return dados


MAC_VALIDO = re.compile(r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$")


class FormDispositivo(FormBootstrap, forms.ModelForm):
    class Meta:
        model = Dispositivo
        fields = ["numero_serie", "mac_ble", "versao_firmware"]
        labels = {
            "numero_serie": "Número de série",
            "mac_ble": "Endereço Bluetooth (MAC)",
            "versao_firmware": "Versão do firmware",
        }
        help_texts = {
            "numero_serie": "Exemplo: BG-0003.",
            "mac_ble": "Seis pares separados por dois-pontos. Exemplo: 24:6F:28:AA:03:03.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilo()

    def clean_mac_ble(self):
        mac = self.cleaned_data["mac_ble"].strip().upper().replace("-", ":")
        if not MAC_VALIDO.match(mac):
            raise forms.ValidationError("Endereço inválido. Use o formato 24:6F:28:AA:03:03.")
        return mac

    def clean_numero_serie(self):
        return self.cleaned_data["numero_serie"].strip().upper()


class FormVinculo(FormBootstrap, forms.Form):
    titular = forms.ModelChoiceField(
        label="Novo titular", queryset=Titular.objects.none(), empty_label="Escolha um titular"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["titular"].queryset = titulares_ativos().order_by("nome")
        self.aplicar_estilo()


class FormFiltroEventos(FormBootstrap, forms.Form):
    inicio = forms.DateField(label="De", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    fim = forms.DateField(label="Até", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    titular = forms.ModelChoiceField(label="Usuário", required=False, queryset=Titular.objects.none(), empty_label="Todos")
    bengala = forms.ModelChoiceField(label="Bengala", required=False, queryset=Dispositivo.objects.none(), empty_label="Todas")
    tipo = forms.ChoiceField(label="Tipo de evento", required=False, choices=[("", "Todos")] + list(ROTULOS_EVENTO.items()))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["titular"].queryset = Titular.objects.order_by("nome")
        self.fields["bengala"].queryset = Dispositivo.objects.order_by("numero_serie")
        self.aplicar_estilo()

    def clean(self):
        dados = super().clean()
        if dados.get("inicio") and dados.get("fim") and dados["inicio"] > dados["fim"]:
            self.add_error("fim", "A data final precisa ser igual ou posterior à inicial.")
        return dados
