# Colocar o site na nuvem: Vercel + TiDB Cloud

O site fica na **Vercel**, com um link fixo `https://<nome>.vercel.app`, e o banco fica no **TiDB Cloud**, que é compatível com MySQL. Os dois têm plano grátis. Depois de pronto, o site funciona com o PC desligado.

```
navegador ──HTTPS──> Vercel (Django: site + API) ──TLS──> TiDB Cloud (banco bengala)
celular   ──HTTPS──/
```

Faça os passos na ordem.

---

## 1. Atualizar o projeto no PC

O driver do banco mudou de `mysqlclient` para `PyMySQL`, que é só Python e instala na Vercel sem compilar nada. No terminal, dentro da pasta do projeto:

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py runserver
```

Se o site abrir como antes, o PC continua funcionando com o MariaDB. **O `.env` do PC não muda.**

---

## 2. Mandar o código para o GitHub

1. Confira se o `bengala.sql` e o `bengala_tidb.sql` **não** aparecem para commit. O `.gitignore` já ignora os dois, porque eles têm os dados e o login dos usuários.
2. Faça o commit e o push da branch `main`.

> Se o repositório começa na pasta de fora (`Documentos\bengala-site`) e o `manage.py` está em `bengala-site\bengala-site`, guarde isso para o passo 4: o **Root Directory** na Vercel vai ser `bengala-site`.

---

## 3. Criar o banco no TiDB Cloud e importar os dados

### 3.1 Criar o cluster

1. Entre em **tidbcloud.com** e crie a conta.
2. Crie um cluster **Starter** (o grátis). Escolha a região mais perto do Brasil.
3. No cluster, clique em **Connect**:
   - clique em **Generate Password** e guarde a senha num lugar seguro;
   - anote o **Host** (algo como `gateway01.xxxx.prod.aws.tidbcloud.com`), a **Port** (`4000`) e o **User** (algo como `xxxxxxxx.root`).

### 3.2 Importar o `bengala_tidb.sql`

O `bengala_tidb.sql` é o seu `bengala.sql` já convertido para o TiDB. Coloque ele na pasta do projeto e rode, trocando `<HOST>` e `<USUARIO>`:

```powershell
& "C:\Program Files\MariaDB 11.8\bin\mysql.exe" -h <HOST> -P 4000 -u <USUARIO> -p --ssl --default-character-set=utf8mb4
```

Digite a senha do TiDB. Dentro do cliente, rode:

```sql
SET GLOBAL tidb_enable_check_constraint = ON;
source bengala_tidb.sql
USE bengala;
SHOW TABLES;
SELECT COUNT(*) FROM evento_deteccao;
exit
```

- A primeira linha liga a verificação dos `CHECK` (bateria entre 0 e 100, tipos de evento etc.). No TiDB ela vem desligada, e sem ela os `CHECK` são ignorados. Se essa linha der erro, pule e continue.
- O `SHOW TABLES` tem que listar as **22 tabelas**, e o `COUNT(*)` tem que dar o mesmo número que no PC (6).

**Se der erro de certificado SSL**, saia e entre de novo trocando `--ssl` por `--ssl --ssl-verify-server-cert=0`. Use isso só para essa importação; o site na Vercel sempre verifica o certificado.

### O que o conversor mudou no arquivo

- Tirou as linhas que só o MariaDB 11 entende, como o `sandbox mode` da primeira linha.
- Nas tabelas `sessao` e `vinculo_dispositivo`, tirou dos `INSERT` os valores das colunas geradas (`dispositivo_em_uso` e `dispositivo_vinculado`). O TiDB calcula essas colunas sozinho e recusa valor nelas.
- Tirou os `LOCK TABLES`, que o TiDB não usa.
- Colocou `AUTO_ID_CACHE=1` nas tabelas, para os IDs novos continuarem em sequência (7, 8, 9...). Sem isso, o TiDB pula para números como 30001.
- Adicionou `CREATE DATABASE bengala` e `USE bengala` no começo.

---

## 4. Publicar na Vercel

1. Entre em **vercel.com** com a conta do GitHub.
2. Clique em **Add New → Project** e escolha o repositório do site.
3. Se o `manage.py` não estiver na raiz do repositório, em **Root Directory** clique em **Edit** e escolha a pasta `bengala-site`.
4. A Vercel reconhece o Django sozinha pelo `manage.py`. Não precisa de `vercel.json`.
5. Abra **Environment Variables** e cadastre as variáveis abaixo, uma por uma:

| Nome | Valor |
|---|---|
| `SECRET_KEY` | uma chave **nova** (veja abaixo) |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `.vercel.app` |
| `CSRF_TRUSTED_ORIGINS` | `https://*.vercel.app` |
| `COOKIE_SEGURO` | `True` |
| `DB_ENGINE` | `django_tidb` |
| `DB_SSL` | `True` |
| `DB_NAME` | `bengala` |
| `DB_USER` | o User do TiDB (`xxxxxxxx.root`) |
| `DB_PASSWORD` | a senha do TiDB |
| `DB_HOST` | o Host do TiDB |
| `DB_PORT` | `4000` |

Para gerar a `SECRET_KEY` nova, no terminal do PC:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Não use a mesma chave do `.env` do PC.

6. Clique em **Deploy**. O CSS, o JavaScript e as fontes saem da pasta `static` sozinhos: a Vercel roda o `collectstatic` no build e serve esses arquivos pela rede dela.

---

## 5. Testar

1. Abra `https://<nome-do-projeto>.vercel.app/entrar/`.
2. Entre com o **mesmo e-mail e senha** do PC. A tabela `auth_user` foi junto na importação.
3. Abra Painel, Usuários, Bengalas, Sensores e Eventos. Os dados têm que ser os mesmos do PC.

Esse link já pode ser enviado para outras pessoas. Só entra quem tem usuário administrador.

### Se der erro

Vá em **Vercel → projeto → Deployments → (último deploy) → Logs**.

| Erro nos logs | O que fazer |
|---|---|
| `DisallowedHost` / erro 400 | conferir `ALLOWED_HOSTS=.vercel.app` (com o ponto no começo) |
| `CSRF verification failed` no login | conferir `CSRF_TRUSTED_ORIGINS=https://*.vercel.app` |
| `Access denied for user` | usuário ou senha do TiDB errados nas variáveis |
| `Connections using insecure transport are prohibited` | faltou `DB_SSL=True` |
| Erro com `django_tidb` ou "Unable to determine Tidb version" | apagar o valor de `DB_ENGINE` (fica o MySQL padrão do Django) e fazer **Redeploy** |
| `KeyError: 'SECRET_KEY'` | faltou cadastrar a `SECRET_KEY` |

Toda vez que mudar uma variável, faça **Redeploy** para ela valer.

---

## 6. Ligar o app do celular

No app NORVATECH:

- **URL base:** `https://<nome-do-projeto>.vercel.app/api/`
- **Token:** o mesmo de antes. A tabela `authtoken_token` também foi importada. Se ainda não existir um token, crie como explicado na seção 3 do `README.md`, com o `.env` do PC apontando para o TiDB (próximo item).

Com HTTPS, o Android aceita a conexão sem liberar tráfego `http` no app.

---

## 7. Usar o banco da nuvem a partir do PC (opcional)

A partir de agora, o banco que vale é o do TiDB. O MariaDB do PC fica só como cópia de testes. Para o `manage.py` do PC (criar usuário, gerar token, `runserver`) trabalhar direto no TiDB, troque no `.env` do PC:

```
DB_ENGINE=django_tidb
DB_SSL=True
DB_NAME=bengala
DB_USER=<User do TiDB>
DB_PASSWORD=<senha do TiDB>
DB_HOST=<Host do TiDB>
DB_PORT=4000
```

Para voltar ao MariaDB, desfaça essas linhas.

---

## 8. O que mudou no código

| Arquivo | Mudança |
|---|---|
| `requirements.txt` | `mysqlclient` → `PyMySQL`; entram `django-tidb` e `certifi`; sai o `gunicorn`, que era do Raspberry Pi |
| `config/settings.py` | usa o PyMySQL; o tipo de banco vem de `DB_ENGINE`; conexão TLS com `DB_SSL=True`; fuso da conexão fixado em `-04:00` (Manaus), para o `CURRENT_TIMESTAMP` do banco bater com o horário do Django também na nuvem, que roda em UTC; reconhece o HTTPS da Vercel |
| `.gitignore` | ignora `bengala.sql`, `bengala_tidb.sql`, `.vercel/` e `.env.local` |
| `.env.exemplo` | novas variáveis `DB_ENGINE` e `DB_SSL` |

O site e a API foram testados com essas mudanças num MySQL 8 com o `bengala_tidb.sql` importado:
- login com CSRF em HTTPS simulado;
- as 5 telas abrindo;
- a API gravando telemetria com token;
- o CSS sendo servido.

A conexão com o TiDB Cloud em si só dá para confirmar no primeiro deploy.
