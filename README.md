# 🗓️ SlotSync — API de Gestão de Agenda

Sistema completo de gestão de agenda com geração de links públicos para verificação de disponibilidade e agendamento de reuniões.

## Stack

- **FastAPI** (Python 3.12) — Backend e API REST
- **PostgreSQL 16** — Banco de dados
- **SQLAlchemy 2 + Alembic** — ORM e migrations
- **Docker + Docker Compose** — Containerização
- **FastMail** — Envio de e-mails
- **JWT** — Autenticação

---

## 🚀 Quick Start (Local)

### 1. Clonar e configurar

```bash
git clone https://github.com/seu-usuario/slotsync.git
cd slotsync
cp .env.example .env
```

### 2. Editar `.env` (opcional)

```env
# Credenciais do banco (padrão já funciona localmente)
POSTGRES_DB=slotsync
POSTGRES_USER=slotsync
POSTGRES_PASSWORD=slotsync_secret

# E-mail (deixe MAIL_ENABLED=false para testar sem e-mail)
MAIL_ENABLED=false
```

### 3. Subir os containers

```bash
docker compose up -d --build
```

### 4. Acessar

| URL | Descrição |
|---|---|
| http://localhost:8010 | Landing page / Login |
| http://localhost:8010/dashboard | Dashboard admin |
| http://localhost:8010/api/docs | Swagger UI |
| http://localhost:8010/api/redoc | ReDoc |

---

## 📌 Como usar

### 1. Criar conta
Acesse http://localhost:8010 e clique em **"Criar conta grátis"**.

### 2. Criar uma agenda
No dashboard → **Minhas Agendas** → **+ Nova agenda**
- Defina nome, duração dos slots, buffer e dias disponíveis

### 3. Gerar link público
No dashboard → **Links Públicos** → **+ Novo link**
- Selecione a agenda
- Copie o link gerado: `http://localhost:8010/book/{token}`

### 4. Compartilhar o link
Seus clientes/convidados acessam o link, escolhem data e horário, preenchem os dados e confirmam. Ambos recebem e-mail de confirmação.

---

## 🌐 API Endpoints

### Autenticação
```
POST /api/auth/register    — Criar conta
POST /api/auth/login       — Login (retorna JWT)
GET  /api/auth/me          — Dados do usuário logado
PUT  /api/auth/me          — Atualizar perfil
```

### Agendas (autenticado)
```
GET    /api/schedules                          — Listar
POST   /api/schedules                          — Criar
PUT    /api/schedules/{id}                     — Atualizar
DELETE /api/schedules/{id}                     — Excluir
POST   /api/schedules/{id}/availability        — Configurar disponibilidade
```

### Links Públicos (autenticado)
```
GET    /api/links              — Listar links
POST   /api/links              — Criar link
PUT    /api/links/{id}/toggle  — Ativar/desativar
DELETE /api/links/{id}         — Excluir
GET    /api/links/bookings     — Listar reuniões
DELETE /api/links/bookings/{id} — Cancelar reunião
```

### Público (sem autenticação)
```
GET  /book/{token}                      — Página de agendamento
GET  /api/public/{token}/slots?date=X   — Slots disponíveis
POST /api/public/{token}/book           — Confirmar agendamento
```

---

## 📧 Configuração de E-mail

Para ativar e-mails de confirmação:

```env
MAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu@gmail.com
SMTP_PASSWORD=sua_senha_de_app  # Senha de app do Google, não a senha normal
EMAILS_FROM_NAME=SlotSync
EMAILS_FROM_EMAIL=seu@gmail.com
```

> **Gmail**: Vá em Configurações → Segurança → Senhas de app e gere uma senha específica para o SlotSync.
> **Alternativas**: SendGrid, Mailgun, Resend (todos têm free tier).

---

## 🐳 Deploy em Servidor

### 1. No servidor, clonar o repositório
```bash
git clone https://github.com/seu-usuario/slotsync.git /opt/slotsync
cd /opt/slotsync
```

### 2. Criar o `.env` de produção
```bash
cp .env.example .env
nano .env  # Editar com valores reais
```

### 3. Subir em produção
```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### 4. CI/CD com GitHub Actions
Configure os secrets no GitHub:
- `SERVER_HOST` — IP ou domínio do servidor
- `SERVER_USER` — Usuário SSH
- `SERVER_SSH_KEY` — Chave SSH privada

Cada push na branch `main` faz deploy automático.

---

## 🏗️ Estrutura do Projeto

```
slotsync/
├── app/
│   ├── main.py              # Entry point FastAPI
│   ├── config.py            # Configurações
│   ├── database.py          # Conexão PostgreSQL
│   ├── models/              # SQLAlchemy (User, Schedule, Booking...)
│   ├── schemas/             # Pydantic (validação de dados)
│   ├── routers/             # Endpoints (auth, schedules, links, public)
│   ├── services/            # Lógica (availability, email, tokens)
│   ├── email_templates/     # Templates HTML de e-mail
│   ├── static/css/          # Estilos globais
│   └── templates/           # HTML (landing, dashboard, booking)
├── alembic/                 # Migrations de banco de dados
├── docker-compose.yml       # Dev
├── docker-compose.prod.yml  # Produção
├── Dockerfile
├── .env.example
└── requirements.txt
```

---

## 🔧 Comandos úteis

```bash
# Ver logs da API
docker compose logs -f api

# Rodar migrations manualmente
docker compose exec api alembic upgrade head

# Acessar banco de dados
docker compose exec db psql -U slotsync -d slotsync

# Rebuild após mudanças de código
docker compose up -d --build api

# Parar tudo
docker compose down

# Parar e remover dados
docker compose down -v
```

---

## 🗄️ Modelo de Dados

```
users               → Usuários multi-tenant
schedules           → Configurações de agenda por usuário
weekly_availability → Regras de horário por dia da semana
public_links        → Links tokenizados de agendamento
bookings            → Reuniões confirmadas
```

---

Feito com ❤️ usando **SlotSync**
