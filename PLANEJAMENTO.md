# 📋 To-Do List — Planejamento do Projeto

> **Objetivo:** desenvolver um aplicativo de lista de tarefas usando **React Native** (frontend) e **Django Rest Framework** (backend), com **autenticação**, **isolamento de dados por usuário** e **documentação completa**.

---

## 1. Visão Geral

O projeto é um aplicativo mobile de gerenciamento de tarefas pessoais. Cada usuário:

- Cria uma conta e faz login no aplicativo;
- Vê **apenas as suas próprias tarefas** (isolamento de dados);
- Pode **criar, listar, editar, concluir e excluir** tarefas (CRUD completo);
- Permanece autenticado entre sessões (token salvo no dispositivo).

### Funcionalidades extras (além do enunciado)

- **Data de vencimento + prioridade** — tarefas com prazo e prioridade (baixa/média/alta), com destaque visual para atrasadas;
- **Busca e filtros** — buscar por título e filtrar por data, prioridade e status;
- **Swipe gestures** — deslizar a tarefa para concluir ou excluir;
- **Modo escuro** — tema claro/escuro seguindo o sistema, com alternância manual;
- **Lixeira (soft delete)** — excluir move para a lixeira, com restauração ou exclusão definitiva;
- **Notificações locais** — lembrete no celular quando a tarefa está para vencer.

### Requisitos do desafio

| Requisito | Como será atendido |
|---|---|
| Frontend mobile | React Native com Expo |
| Backend REST | Django + Django Rest Framework |
| Autenticação segura | Token nativo do DRF (`TokenAuthentication`) |
| Isolamento de dados por usuário | Queryset filtrado por `request.user` em todas as views |
| Documentação completa | READMEs + Swagger/OpenAPI automático (drf-spectacular) |

---

## 2. Stack Tecnológica

### Backend

| Tecnologia | Papel |
|---|---|
| Python 3.12+ | Linguagem |
| Django 5.x | Framework web (ORM, migrations, admin) |
| Django Rest Framework | Camada de API REST |
| `rest_framework.authtoken` | Autenticação por token (nativa do DRF) |
| drf-spectacular | Documentação automática Swagger/OpenAPI |
| django-filter | Busca e filtros na API (título, data, prioridade, status) |
| django-cors-headers | Liberar acesso do app mobile à API |
| SQLite | Banco de dados em desenvolvimento (zero configuração) |
| python-dotenv | Variáveis de ambiente (`SECRET_KEY`, `DEBUG`, etc.) |

### Frontend

| Tecnologia | Papel |
|---|---|
| React Native (Expo) | Framework mobile — roda no celular via Expo Go, sem Android Studio |
| JavaScript | Linguagem (migrar para TypeScript é opcional no futuro) |
| React Navigation | Navegação entre telas (stack de auth × stack do app) |
| Axios | Cliente HTTP para consumir a API |
| Expo SecureStore | Armazenamento **seguro** do token no dispositivo |
| Context API (React) | Estado global de autenticação (`AuthContext`) e de tema (`ThemeContext`) |
| react-native-gesture-handler + Reanimated | Swipe gestures (concluir/excluir ao deslizar) |
| expo-notifications | Notificações locais de lembrete de vencimento |
| datetimepicker (community) | Seleção de data/hora de vencimento no formulário |

---

## 3. Arquitetura Geral

```
┌─────────────────────────┐         HTTP/JSON          ┌──────────────────────────┐
│   APP MOBILE            │ ─────────────────────────▶ │   API REST               │
│   React Native (Expo)   │   Authorization:           │   Django + DRF           │
│                         │   Token <token>            │                          │
│  Telas ── AuthContext   │ ◀───────────────────────── │  Views ── Serializers    │
│    │         │          │        respostas JSON      │    │          │          │
│  Axios   SecureStore    │                            │  Models ─── ORM          │
└─────────────────────────┘                            └───────────┬──────────────┘
                                                                   │
                                                             ┌─────▼─────┐
                                                             │  SQLite   │
                                                             │  (dev)    │
                                                             └───────────┘
```

**Fluxo de uma requisição autenticada:**

1. O usuário abre o app; o `AuthContext` lê o token salvo no SecureStore.
2. O Axios anexa o header `Authorization: Token <token>` em toda requisição.
3. O DRF valida o token e identifica o `request.user`.
4. A view filtra o queryset pelo usuário autenticado e responde em JSON.
5. O app atualiza a tela com os dados recebidos.

---

## 4. Estrutura de Pastas

O projeto é um **monorepo** com duas pastas raiz — `backend/` e `frontend/` — totalmente independentes entre si:

```
to-do-list/
├── README.md                  # Documentação geral: visão, setup, como rodar tudo
├── .gitignore                 # Ignora venv, node_modules, .env, db.sqlite3, etc.
├── backend/                   # API Django Rest Framework
└── frontend/                  # App React Native (Expo)
```

### 4.1. Backend (`backend/`)

```
backend/
├── manage.py                      # Ponto de entrada dos comandos Django
├── requirements.txt               # Dependências Python fixadas (pip freeze)
├── .env.example                   # Modelo das variáveis de ambiente (sem segredos)
├── README.md                      # Doc do backend: setup, endpoints, testes
│
├── config/                        # Projeto Django (configuração global)
│   ├── __init__.py
│   ├── settings.py                # INSTALLED_APPS, DRF, authtoken, CORS, spectacular
│   ├── urls.py                    # Rotas raiz: /api/auth/, /api/tasks/, /api/docs/
│   ├── wsgi.py                    # Entrada para servidor de produção
│   └── asgi.py                    # Entrada assíncrona (padrão do Django)
│
├── accounts/                      # App de autenticação e usuários
│   ├── __init__.py
│   ├── apps.py                    # Configuração do app
│   ├── serializers.py             # RegisterSerializer (validação de senha/e-mail)
│   ├── views.py                   # RegisterView, LoginView (retorna token), LogoutView
│   ├── urls.py                    # /register/, /login/, /logout/
│   └── tests.py                   # Testes de registro, login e logout
│
└── tasks/                         # App de tarefas (domínio principal)
    ├── __init__.py
    ├── apps.py                    # Configuração do app
    ├── models.py                  # Model Task (FK User, vencimento, prioridade, lixeira)
    ├── serializers.py             # TaskSerializer (user somente leitura)
    ├── filters.py                 # TaskFilter: busca por título, data, prioridade, status
    ├── views.py                   # TaskViewSet (CRUD isolado + lixeira/restore + filtros)
    ├── urls.py                    # Router do DRF: /api/tasks/ e /api/tasks/{id}/
    ├── admin.py                   # Registro do Task no Django Admin
    ├── migrations/                # Histórico de migrações do banco
    │   └── __init__.py
    └── tests.py                   # Testes de CRUD e de isolamento entre usuários
```

**Responsabilidade de cada app:**

- **`config/`** — apenas configuração; não contém regra de negócio.
- **`accounts/`** — tudo sobre identidade: criar conta, entrar (gerar token), sair (invalidar token). Usa o model `User` **nativo do Django**, sem customização.
- **`tasks/`** — o domínio do app: model, serializer e viewset de tarefas, sempre amarrados ao usuário autenticado.

### 4.2. Frontend (`frontend/`)

```
frontend/
├── App.js                         # Raiz: envolve o app com AuthProvider + navegação
├── app.json                       # Configuração do Expo (nome, ícone, splash)
├── package.json                   # Dependências JavaScript
├── babel.config.js                # Configuração padrão do Expo
├── .env.example                   # Modelo: URL base da API
├── README.md                      # Doc do frontend: setup, como rodar no celular
│
├── assets/                        # Ícone, splash screen, imagens
│
└── src/
    ├── screens/                   # Uma pasta/arquivo por tela
    │   ├── LoginScreen.js         # Formulário de login → salva token → entra no app
    │   ├── RegisterScreen.js      # Formulário de cadastro → cria conta → faz login
    │   ├── TaskListScreen.js      # Lista com busca/filtros + swipe p/ concluir/excluir
    │   ├── TaskFormScreen.js      # Criar/editar tarefa (título, descrição,
    │   │                          #   vencimento e prioridade)
    │   └── TrashScreen.js         # Lixeira: restaurar ou excluir definitivamente
    │
    ├── components/                # Componentes reutilizáveis
    │   ├── TaskItem.js            # Card da tarefa com swipe (checkbox, título,
    │   │                          #   badge de prioridade, vencimento/atrasada)
    │   ├── Input.js               # Campo de texto padronizado dos formulários
    │   └── Button.js              # Botão padronizado (loading, disabled)
    │
    ├── navigation/
    │   └── AppNavigator.js        # Decide a stack: deslogado (Login/Registro)
    │                              #   × logado (Lista/Formulário de tarefas)
    │
    ├── contexts/
    │   ├── AuthContext.js         # Estado global: user, token, signIn(), signOut()
    │   └── ThemeContext.js        # Modo claro/escuro: segue o sistema + toggle manual
    │
    ├── services/
    │   ├── api.js                 # Instância do Axios + interceptor que injeta o token
    │   ├── authService.js         # Chamadas: register, login, logout
    │   ├── taskService.js         # Chamadas: listar (com filtros), criar, atualizar,
    │   │                          #   excluir, lixeira e restaurar tarefas
    │   └── notificationService.js # Agenda/cancela lembretes locais (expo-notifications)
    │
    └── storage/
        └── tokenStorage.js        # Salvar/ler/apagar token no Expo SecureStore
```

**Regra de organização:** telas não chamam o Axios diretamente — sempre passam pelos `services/`. Isso concentra a comunicação com a API em um só lugar e facilita testes e manutenção.

---

## 5. Modelagem de Dados

### `User` — nativo do Django (`django.contrib.auth.models.User`)

Não será criado model customizado; o usuário padrão já oferece `username`, `email`, `password` (com hash seguro) e integração pronta com o `authtoken`.

### `Task` — app `tasks`

| Campo | Tipo | Detalhes |
|---|---|---|
| `id` | AutoField | Chave primária (automática) |
| `user` | ForeignKey → User | **Dono da tarefa** — base do isolamento de dados (`on_delete=CASCADE`) |
| `title` | CharField(200) | Título da tarefa (obrigatório) |
| `description` | TextField | Descrição detalhada (opcional, `blank=True`) |
| `completed` | BooleanField | Concluída ou não (`default=False`) |
| `due_date` | DateTimeField | **Data de vencimento** (opcional, `null=True`) — base dos lembretes e do destaque de atrasadas |
| `priority` | CharField(choices) | **Prioridade**: `baixa` / `media` / `alta` (`default="media"`) |
| `deleted_at` | DateTimeField | `null=True` — quando preenchido, a tarefa está na **lixeira** (soft delete) |
| `created_at` | DateTimeField | `auto_now_add=True` |
| `updated_at` | DateTimeField | `auto_now=True` |

```
User (1) ──────< (N) Task
```

**Como funciona a lixeira (soft delete):** `DELETE /api/tasks/{id}/` não apaga o registro — apenas preenche `deleted_at`. O queryset padrão do `TaskViewSet` filtra `deleted_at__isnull=True`, então itens na lixeira somem das listagens normais; eles só aparecem em `/api/tasks/trash/`, de onde podem ser **restaurados** (`deleted_at = None`) ou **excluídos definitivamente**.

---

## 6. Endpoints da API

Todas as rotas ficam sob o prefixo `/api/`.

### Autenticação (`accounts`)

| Método | Rota | Autenticado? | Descrição |
|---|---|---|---|
| POST | `/api/auth/register/` | Não | Cria a conta do usuário |
| POST | `/api/auth/login/` | Não | Valida credenciais e **retorna o token** |
| POST | `/api/auth/logout/` | Sim | Apaga o token do usuário no servidor |

### Tarefas (`tasks`)

| Método | Rota | Autenticado? | Descrição |
|---|---|---|---|
| GET | `/api/tasks/` | Sim | Lista **apenas** as tarefas do usuário logado (aceita busca e filtros) |
| POST | `/api/tasks/` | Sim | Cria tarefa já vinculada ao usuário logado |
| GET | `/api/tasks/{id}/` | Sim | Detalha uma tarefa (se for do usuário) |
| PUT / PATCH | `/api/tasks/{id}/` | Sim | Atualiza uma tarefa (se for do usuário) |
| DELETE | `/api/tasks/{id}/` | Sim | **Move para a lixeira** (soft delete) |
| GET | `/api/tasks/trash/` | Sim | Lista as tarefas na lixeira do usuário |
| POST | `/api/tasks/{id}/restore/` | Sim | Restaura uma tarefa da lixeira |
| DELETE | `/api/tasks/{id}/permanent/` | Sim | Exclui **definitivamente** (só para itens já na lixeira) |

**Busca e filtros em `GET /api/tasks/`** (via django-filter):

```
?search=mercado           → busca pelo título
?due_date=2026-07-10      → tarefas que vencem nesse dia
?due_date__lte=2026-07-10 → tarefas que vencem até essa data
?priority=alta            → filtra por prioridade
?completed=false          → filtra por status
?ordering=due_date        → ordena por vencimento (-due_date inverte)
```

### Documentação

| Rota | Descrição |
|---|---|
| `/api/docs/` | Swagger UI interativo (drf-spectacular) |
| `/api/schema/` | Schema OpenAPI em JSON/YAML |

### Exemplos de request/response

**`POST /api/auth/login/`**

```json
// Request
{ "username": "wendel", "password": "senha-secreta" }

// Response 200
{ "token": "9f2b1c8e4a7d...", "user": { "id": 1, "username": "wendel" } }
```

**`POST /api/tasks/`** (com header `Authorization: Token 9f2b1c8e4a7d...`)

```json
// Request
{
  "title": "Estudar DRF",
  "description": "Ler a doc de ViewSets",
  "due_date": "2026-07-10T18:00:00Z",
  "priority": "alta"
}

// Response 201
{
  "id": 12,
  "title": "Estudar DRF",
  "description": "Ler a doc de ViewSets",
  "completed": false,
  "due_date": "2026-07-10T18:00:00Z",
  "priority": "alta",
  "deleted_at": null,
  "created_at": "2026-07-08T14:30:00Z",
  "updated_at": "2026-07-08T14:30:00Z"
}
```

---

## 7. Fluxo de Autenticação

```
┌──────────┐   1. POST /register/    ┌──────────┐
│  Usuário │ ──────────────────────▶ │   API    │  cria User
│  (app)   │   2. POST /login/       │  (DRF)   │  valida senha
│          │ ◀────────────────────── │          │  devolve Token
└────┬─────┘        { token }        └──────────┘
     │
     │ 3. salva o token no Expo SecureStore
     │ 4. toda requisição seguinte leva:  Authorization: Token <token>
     │ 5. logout → POST /logout/ (apaga no servidor) + apaga do SecureStore
```

Pontos importantes:

- **Registro:** o `RegisterSerializer` valida senha (força mínima do Django) e e-mail único; a senha é sempre armazenada com hash.
- **Login:** usa `obtain_auth_token` do DRF (ou view própria que retorna token + dados do usuário).
- **Armazenamento no app:** o token fica no **SecureStore** (criptografado pelo sistema operacional), não em texto plano.
- **Sessão persistente:** ao abrir o app, o `AuthContext` verifica se há token salvo; se houver, o usuário cai direto na lista de tarefas.
- **Logout:** invalida o token no servidor (delete no banco) **e** remove do dispositivo.

---

## 8. Isolamento de Dados por Usuário

Nenhum usuário pode ver, editar ou excluir tarefas de outro. Três camadas garantem isso no backend:

**1. Exigir autenticação em tudo** — configuração global no `settings.py`:

```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.TokenAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}
```

**2. Listar/acessar apenas o que é do usuário** — no `TaskViewSet`:

```python
def get_queryset(self):
    return Task.objects.filter(user=self.request.user)
```

Como o detalhe (`/api/tasks/{id}/`) também parte desse queryset, acessar a tarefa de outro usuário resulta em **404** — nem revela que ela existe.

**3. Criar sempre em nome do usuário logado** — o campo `user` nunca vem do cliente:

```python
def perform_create(self, serializer):
    serializer.save(user=self.request.user)
```

No serializer, `user` é somente leitura, impedindo que o cliente tente atribuir a tarefa a outra pessoa.

**Teste obrigatório:** `tasks/tests.py` terá um teste em que o usuário B tenta ler/editar/excluir uma tarefa do usuário A e recebe 404.

---

## 9. Telas do App

| Tela | Stack | Responsabilidade |
|---|---|---|
| `LoginScreen` | Deslogado | Formulário de login; em caso de sucesso salva o token e troca de stack |
| `RegisterScreen` | Deslogado | Formulário de cadastro; após criar a conta, faz login automático |
| `TaskListScreen` | Logado | Lista com **busca por título e filtros por data/prioridade/status**; **swipe** para concluir (direita) ou excluir (esquerda, com desfazer); acesso à lixeira, alternância de tema, logout e nova tarefa |
| `TaskFormScreen` | Logado | Formulário único para **criar** e **editar**, com campos de **vencimento** (date picker) e **prioridade**; ao salvar, agenda o lembrete local |
| `TrashScreen` | Logado | **Lixeira**: lista as tarefas excluídas, com ações de restaurar e excluir definitivamente |

**Navegação (`AppNavigator`):**

```
AuthContext.token existe?
├── NÃO  → Stack de autenticação: Login ⇄ Registro
└── SIM  → Stack do app: Lista de Tarefas ─┬─→ Formulário de Tarefa
                                           └─→ Lixeira
```

### Comportamentos das funcionalidades extras

- **Modo escuro** — o `ThemeContext` inicia seguindo o tema do sistema (`useColorScheme`) e permite alternância manual; a preferência fica salva no dispositivo.
- **Notificações locais** — ao salvar tarefa com `due_date`, o `notificationService` agenda um lembrete local para o horário do vencimento; concluir, excluir ou mudar a data reagenda/cancela a notificação. Tudo via `expo-notifications`, sem servidor de push.
- **Swipe** — deslizar para a direita conclui/reabre a tarefa; para a esquerda move para a lixeira, exibindo um aviso "Desfazer" por alguns segundos antes de confirmar.
- **Atrasadas** — tarefas com `due_date` no passado e não concluídas ganham destaque visual na lista.

---

## 10. Documentação do Projeto

| Documento | Conteúdo |
|---|---|
| `README.md` (raiz) | Visão geral, arquitetura, pré-requisitos, como subir backend + frontend juntos |
| `backend/README.md` | Setup do ambiente Python, migrações, como rodar servidor e testes, tabela de endpoints |
| `frontend/README.md` | Setup do Node/Expo, como configurar a URL da API, como rodar no celular/emulador |
| Swagger (`/api/docs/`) | Documentação **viva** da API, gerada automaticamente pelo drf-spectacular a partir do código |
| `.env.example` (ambos) | Lista das variáveis de ambiente necessárias, sem valores sensíveis |

---

## 11. Roadmap de Implementação

| Fase | Entrega | Critério de conclusão |
|---|---|---|
| **1. Setup do backend** | Projeto Django criado, apps `accounts` e `tasks`, model `Task`, migrações, admin | `python manage.py runserver` sobe sem erros; Task visível no admin |
| **2. Autenticação** | Registro, login (token) e logout funcionando | Fluxo completo testável via Swagger/curl |
| **3. CRUD com isolamento** | `TaskViewSet` completo + testes de isolamento | Testes passam; usuário B recebe 404 na tarefa do usuário A |
| **4. Setup do frontend** | Projeto Expo criado, navegação, `AuthContext`, telas de Login/Registro integradas à API | Login real pelo app salva token e troca de stack |
| **5. Telas de tarefas** | Lista + formulário integrados (criar, editar, concluir, excluir) | CRUD completo funcionando no celular |
| **6. Documentação e ajustes** | READMEs finalizados, Swagger revisado, `.env.example`, revisão geral | Uma pessoa nova consegue rodar o projeto só lendo os READMEs |
| **7. Extras — backend** | `due_date` + `priority` no model, lixeira (soft delete, trash, restore, permanent), busca e filtros com django-filter, testes dos novos fluxos | Filtros e lixeira funcionando via Swagger; testes cobrem restaurar, excluir definitivo e filtros |
| **8. Extras — frontend** | Swipe gestures, modo escuro, campos de vencimento/prioridade no formulário, busca/filtros na lista, tela de lixeira, notificações locais | No celular: criar tarefa com vencimento → receber lembrete; swipe conclui/exclui com desfazer; tema escuro aplicado em todas as telas |

---

*Documento de planejamento — nenhum código foi implementado ainda. A implementação seguirá as fases do roadmap acima.*
