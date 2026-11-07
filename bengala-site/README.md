# Bengala Inteligente: site administrativo e API

Site em Django para administrar o banco da bengala, e API (Django REST Framework) que recebe os dados do app Android.

- **Site:** 6 telas (Login, Painel, Usuários, Bengalas, Sensores, Eventos). Só administradores entram.
- **API:** rotas para o app, com autenticação por token.
- **Banco:** MariaDB/MySQL com as 12 tabelas do `schema.sql`. O Django **não cria nem altera** essas tabelas.

```
celular (app) --HTTPS + token--> Django (API) --> MariaDB (só localhost)
navegador     --login----------> Django (site) -/
```

---

## 1. Estrutura

```
bengala-site/
├── config/            settings.py (lê o .env), urls.py, wsgi.py
├── core/              models.py (12 tabelas, managed = False) e consultas.py
├── painel/            telas do site: views, forms, templates, CSS/JS
│   └── static/vendor/ Bootstrap, ícones, fonte, Leaflet e Chart.js (servidos localmente)
├── api/               serializers, views e rotas da API
├── deploy/            serviço do systemd e usuários do banco
├── requirements.txt
└── .env.exemplo
```

---

## 2. Rodar no PC (desenvolvimento)

### 2.1 Banco

1. Instale o MariaDB (ou o XAMPP, ou o MySQL 8.0.16+).
2. Como **root**, rode nesta ordem:
   1. `schema.sql`
   2. `dados_teste.sql`
   3. `deploy/usuarios_banco.sql` (troque as senhas antes)

### 2.2 Python

Windows (PowerShell):

```powershell
cd bengala-site
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.exemplo .env
```

Linux / Raspberry Pi:

```bash
sudo apt install -y python3-venv python3-dev build-essential pkg-config libmariadb-dev
cd bengala-site
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.exemplo .env
```

Abra o `.env` e preencha `SECRET_KEY` e `DB_PASSWORD`. Para gerar a chave:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 2.3 Tabelas do Django (uma vez só, com root)

O usuário `api_bengala` não tem permissão para criar tabelas, e isso é de propósito. Por isso o `migrate` roda **uma vez** com o root. Ele cria só as tabelas do Django (`auth_user`, `django_session`, `authtoken_token` etc.) e não toca nas 12 tabelas do projeto, porque todas estão com `managed = False`.

Para usar o root só neste comando, troque temporariamente no `.env`:

```
DB_USER=root
DB_PASSWORD=senha-do-root
```

Depois rode:

```bash
python manage.py migrate
python manage.py createsuperuser
```

No `createsuperuser`, **preencha o e-mail**: o login do site é feito pelo e-mail.

Por fim, volte o `.env` para `api_bengala`.

### 2.4 Subir o site

```bash
python manage.py runserver
```

Abra http://127.0.0.1:8000 e entre com o e-mail e a senha do superusuário.

---

## 3. Token do app

O app não usa usuário nem senha do banco. Ele usa um token da API. Para criar um usuário só para o app (ele **não** consegue entrar no site, porque não é administrador) e gerar o token:

```bash
python manage.py shell -c "from django.contrib.auth.models import User; User.objects.create_user('app_celular')"
python manage.py drf_create_token app_celular
```

O comando imprime a chave. O app deve mandar em toda requisição o cabeçalho:

```
Authorization: Token <chave>
```

---

## 4. Rotas da API

Base: `http://<servidor>:8000/api/`. Todas exigem o token. Datas no formato `2026-11-07T10:00:00`; se vierem com fuso (`-04:00` ou `Z`), o servidor converte para o horário de Manaus.

| Método | Rota | O que faz | Corpo (JSON) |
|---|---|---|---|
| POST | `/api/sessoes` | abre uma sessão de uso | `dispositivo_id`, opcionais `titular_id` e `inicio` |
| PATCH | `/api/sessoes/{id}` | encerra a sessão | opcionais `fim`, `distancia_m` |
| POST | `/api/sessoes/{id}/eventos` | recebe um **lote** de detecções | lista de `{tipo, nivel_alerta, distancia_cm, latitude, longitude, ocorrido_em}` |
| POST | `/api/sos` | registra queda ou botão | `sessao_id`, `origem`, opcionais `confirmado_por`, `latitude`, `longitude`, `disparado_em` |
| PATCH | `/api/sos/{id}` | cancela ou marca como atendido | `status` (`CANCELADO` ou `ATENDIDO`), opcional `cancelado_em` |
| POST | `/api/telemetria` | bateria e sinal BLE | `dispositivo_id`, `bateria_pct`, opcionais `rssi_ble`, `registrado_em` |
| GET | `/api/mapa/buracos` | pontos agregados do mapa colaborativo | parâmetro opcional `?minimo=3` |

Regras importantes:

- **Lote em transação:** se um evento do lote estiver errado, nenhum é gravado e a resposta é 400, dizendo qual item falhou. O **201 só sai depois de gravar**: é ele que o app usa para marcar a fila local como sincronizada.
- **Sessão:** o titular e o vínculo são descobertos pelo `dispositivo_id`. Se a bengala já tiver uma sessão aberta, a resposta é **409**, com `sessao_aberta_id` (o schema só aceita uma sessão aberta por bengala).
- **LGPD:** se o titular não deu `consentimento_localizacao`, a API **descarta latitude e longitude** antes de gravar.
- **S.O.S.:** a API só registra o histórico. O aviso aos contatos sai direto do celular.
- **Coordenadas** com muitas casas decimais (GPS do Android) são arredondadas para 7, como no banco.

Testes rápidos com curl (no Windows, use o Insomnia ou o Postman com o mesmo corpo):

```bash
TOKEN=cole-a-chave-aqui
API=http://127.0.0.1:8000/api

curl -X POST $API/telemetria -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
  -d '{"dispositivo_id": 1, "bateria_pct": 74, "rssi_ble": -57}'

curl -X POST $API/sessoes -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
  -d '{"dispositivo_id": 1}'

curl -X POST $API/sessoes/3/eventos -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
  -d '[{"tipo":"BURACO","nivel_alerta":3,"distancia_cm":69.2,"latitude":-3.131234,"longitude":-60.024011,"ocorrido_em":"2026-11-07T10:01:00"},
       {"tipo":"OBSTACULO","nivel_alerta":2,"distancia_cm":95,"ocorrido_em":"2026-11-07T10:02:00"}]'

curl -X PATCH $API/sessoes/3 -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
  -d '{"distancia_m": 850}'
```

---

## 5. Telas e de onde vêm os dados

| Tela | Mostra | Tabelas |
|---|---|---|
| Login | e-mail, senha, manter conectado | `auth_user` |
| Painel | contadores, detecções por dia (7 dias), última localização no mapa, buracos recorrentes, status das bengalas, últimos eventos | `titular`, `dispositivo`, `vinculo_dispositivo`, `evento_deteccao`, `alerta_sos`, `telemetria` |
| Usuários | busca, status, ver, cadastrar, editar, desativar e reativar; contatos, bengalas, sessões e S.O.S. de cada um | `titular`, `contato_emergencia`, `vinculo_dispositivo`, `sessao`, `alerta_sos` |
| Bengalas | lista, usuário associado, bateria, conexão, cadastrar, editar, trocar titular, desativar, calibração, histórico de titulares e de uso | `dispositivo`, `vinculo_dispositivo`, `configuracao`, `telemetria`, `sessao` |
| Sessão (a partir das duas acima) | detecções, S.O.S. e avisos enviados, navegação | `sessao`, `evento_deteccao`, `alerta_sos`, `notificacao_sos`, `trajeto` |
| Sensores | bateria e sinal atuais, gráfico das últimas 50 leituras, última detecção de cada sensor, calibração | `telemetria`, `evento_deteccao`, `alerta_sos`, `configuracao` |
| Eventos | histórico com filtros por data, usuário, bengala e tipo, paginado | `evento_deteccao` + `alerta_sos` + `telemetria` (bateria ≤ 15%) |

Cálculos:

- **Conectada:** telemetria recebida nos últimos 5 minutos (`MINUTOS_CONECTADA` em `core/consultas.py`).
- **Bateria baixa:** telemetria com até 15% (`BATERIA_BAIXA_PCT`).
- **Localização:** só aparece para titulares com consentimento. Para os outros, o site mostra "Oculta (sem consentimento)".
- **Buracos recorrentes:** buracos agrupados por coordenada arredondada em 4 casas (cerca de 11 m), com 3 ou mais ocorrências. O trajeto de uma pessoa nunca é desenhado.
- **Desativar** (usuário ou bengala) preenche `excluido_em`. Nada é apagado com DELETE, como manda o schema.
- **Trocar titular** encerra o vínculo atual (`data_fim`) e cria um novo. Só é permitido sem sessão aberta.

---

## 6. Diferenças entre o PDF e o `schema.sql` (vale o schema)

| PDF | `schema.sql` | O que o site faz |
|---|---|---|
| 11 tabelas, tabela `usuario` | 12 tabelas, tabela `titular` | a tela continua se chamando "Usuários" e usa `titular` |
| bengala ligada direto ao usuário | dono definido em `vinculo_dispositivo`, com histórico | tela de troca de titular e histórico de titulares |
| pendente: coluna `ativo` em `usuario` | `excluido_em` em `titular`, `dispositivo` e `contato_emergencia` | botões Desativar e Reativar usam `excluido_em` (**pendência resolvida**) |
| pendente: tipos Queda, Bateria baixa e Desconectado | não há view `vw_eventos` | a tela Eventos junta as 3 tabelas com `UNION ALL` no ORM, sem mexer no banco (**resolvido**). "Desconectado" é um status calculado, não um evento |
| pendente: `modelo` e `observacoes` em `dispositivo` | não existem; há `numero_serie` | o site mostra número de série, MAC e firmware; modelo e observações ficam de fora |
| pendente: leituras brutas dos sensores | não são gravadas | Sensores mostra bateria, sinal e a última detecção de cada sensor (**continua pendente** se quiserem leituras contínuas) |

Detalhes técnicos dos models:

- As colunas geradas `dispositivo_vinculado` e `dispositivo_em_uso` não estão nos models. O MariaDB calcula sozinho e recusaria INSERT nelas.
- O Django não tem chave estrangeira composta. As FKs compostas viraram FKs simples nos models; quem garante a coerência continua sendo o banco.

---

## 7. Produção no Raspberry Pi 5

1. Banco já instalado conforme `banco-dados-raspberry-pi.md` (dados no SSD, `bind-address = 127.0.0.1`).
2. Copie o projeto para `/home/pi/bengala-site` e faça os passos 2.2 e 2.3.
3. No `.env`: `DEBUG=False`, `ALLOWED_HOSTS` com o IP do Pi e o nome no Tailscale, e o mesmo em `CSRF_TRUSTED_ORIGINS` (com `http://` e a porta).
4. Junte os arquivos estáticos (CSS, JS, fontes):

   ```bash
   python manage.py collectstatic --noinput
   ```

5. Instale o serviço para subir sozinho no boot:

   ```bash
   sudo cp deploy/bengala-site.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now bengala-site
   systemctl status bengala-site
   ```

6. Acesse `http://<ip-do-pi>:8000`. Fora de casa, só pelo Tailscale. A porta 3306 nunca é aberta.

O `runserver` é só para desenvolvimento. No Pi quem roda é o gunicorn. Os avisos de HTTPS do `python manage.py check --deploy` são esperados enquanto o acesso for por rede local ou Tailscale. Se um dia o site for para HTTPS, coloque `COOKIE_SEGURO=True`.

Bootstrap, ícones, fonte, Leaflet e Chart.js estão em `painel/static/vendor/`, então o site funciona sem internet. Só os blocos do mapa (OpenStreetMap) precisam de rede.

---

## 8. Critérios de pronto

- [x] Login funciona e bloqueia todas as telas para quem não está logado (e para quem não é administrador)
- [x] As 6 telas abrem com os dados de `dados_teste.sql`, sem números fixos no HTML
- [x] Filtros e paginação de Eventos e Usuários
- [x] Mapa (Leaflet) e gráficos (Chart.js), com tabela alternativa para leitor de tela
- [x] Rotas da API testadas, incluindo lote de eventos (transação, erro em um item e lote vazio)
- [x] Nenhuma tabela do projeto criada ou alterada por migration
- [ ] Rodar no Raspberry Pi com gunicorn e systemd (arquivo pronto em `deploy/`; falta testar no Pi)
- [ ] Código no Git

Os testes foram feitos com o `schema.sql` e o `dados_teste.sql` carregados num banco de teste. A primeira execução no MariaDB de vocês é a confirmação final.

---

## 9. O que muda no app Android

1. **Token:** adicionar um interceptor do OkHttp que envie `Authorization: Token <chave>`, mais um campo nas configurações para guardar a chave.
2. **URL base** terminando em `/api/` (ex.: `http://192.168.0.50:8000/api/`).
3. **Abrir sessão:** basta `dispositivo_id`. O `usuario_id` que o app manda hoje é ignorado. A resposta traz `id`.
4. **Encerrar sessão:** chamar `PATCH sessoes/{id}` ao desligar. Se não encerrar, a próxima abertura recebe 409 com o `sessao_aberta_id`.
5. Trocar os textos "FastAPI" por "Django" (README e tela Sobre).
