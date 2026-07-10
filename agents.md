# 🤖 Agents — Pipeline de Revisão Obrigatória

Este arquivo define o **processo de validação de toda demanda finalizada** neste projeto.
Nenhuma alteração de código é considerada concluída sem passar pelos quatro agentes abaixo.

---

## Regra Geral (o loop de aprovação)

```
┌────────────────────┐
│  Demanda concluída │
│  (código alterado) │
└─────────┬──────────┘
          ▼
┌─────────────────────────────────────────┐
│  As alterações são apresentadas aos     │
│  4 agentes, nesta ordem:                │
│                                         │
│  1️⃣ agent-security                      │
│  2️⃣ agent-qualidade                     │
│  3️⃣ agent-cobertura                     │
│  4️⃣ agent-teste-real  (principal)       │
└─────────┬───────────────────────────────┘
          ▼
   Todos aprovaram? ──── SIM ──▶ ✅ Alteração PASSA (demanda encerrada)
          │
         NÃO
          ▼
┌─────────────────────────────────────────┐
│  ❌ O agente que negou registra o(s)    │
│  motivo(s). O código volta para ser     │
│  REFEITO corrigindo exatamente esses    │
│  pontos, e o ciclo recomeça do agente 1 │
└─────────────────────────────────────────┘
          │
          └──────▶ repete até aprovação unânime
```

### Regras do loop

1. **Unanimidade obrigatória** — a alteração só passa se os **quatro** agentes aprovarem.
2. **Uma negação basta** — se qualquer agente reprovar, o código é refeito e o ciclo **recomeça do agente 1** (uma correção pode introduzir problema novo em área já aprovada).
3. **Reprovação sempre vem com motivo** — o agente que nega deve listar, ponto a ponto, o que precisa ser corrigido. Reprovar sem justificativa não é permitido.
4. **A correção ataca só os motivos listados** — não se reescreve o que já foi aprovado sem necessidade.
5. **Trava de segurança do loop** — após **3 reprovações consecutivas** da mesma demanda, o loop pausa e o problema é apresentado ao usuário com o histórico de motivos, para decisão humana (evita loop infinito).

### Formato do veredito (padrão para os 3 agentes)

```
AGENTE: <nome>
VEREDITO: ✅ APROVADO | ❌ REPROVADO
MOTIVOS (se reprovado):
  1. <problema encontrado> — <arquivo/trecho> — <o que deve ser feito>
  2. ...
```

---

## 1️⃣ agent-security 🔐

**Papel:** guardião da segurança da API e dos dados dos usuários.

### O que ele valida em toda alteração

- **Endpoints protegidos** — toda rota que manipula dados exige autenticação (`IsAuthenticated` + `TokenAuthentication`); nenhuma rota nova pode nascer aberta por acidente.
- **Injeção de dados** — testa entradas maliciosas nos campos e parâmetros (SQL injection, payloads inesperados, campos extras no JSON tentando escalar privilégio, ex.: enviar `"user": 2` no corpo para gravar tarefa em nome de outro usuário).
- **Isolamento entre usuários** — usuário sem login **não acessa nada**; usuário logado **não vê, edita ou apaga dados de outro** (a tentativa deve resultar em 401/404, nunca em vazamento).
- **Segredos e infraestrutura** — `SECRET_KEY`, senhas e tokens nunca em código ou commit; `DEBUG=False` fora de dev; CORS restrito; senhas sempre com hash.

### Quando ele NEGA

> Se a alteração for **perigosa** — afetar a infraestrutura, abrir brecha de autenticação, permitir injeção ou vazamento de dados — o veredito é ❌ REPROVADO e o código **deve ser refeito**, com a lista exata das brechas encontradas.

### Exemplos de reprovação automática

- Endpoint novo sem `permission_classes`.
- Queryset sem filtro por `request.user`.
- Serializer aceitando o campo `user` como gravável.
- Credencial ou segredo hardcoded no código.

---

## 2️⃣ agent-qualidade 🧹

**Papel:** guardião da consistência, legibilidade e robustez lógica do código.

### O que ele valida em toda alteração

- **Consistência** — o código novo segue os padrões já existentes no projeto (estrutura de pastas do `PLANEJAMENTO.md`, telas chamando `services/` e nunca o Axios direto, nomenclatura, idioma dos textos).
- **Qualidade** — sem código morto, sem duplicação desnecessária, funções com responsabilidade única, tratamento de erro nas chamadas à API (o app não pode quebrar se a rede falhar).
- **Risco de quebra de lógica** — estados impossíveis, condições invertidas, `null`/`undefined` não tratados, efeitos colaterais escondidos, migração de banco que perde dados.
- **Falha de sistema** — mudanças que podem derrubar o servidor ou travar o app (loop sem saída, requisição em cascata, exceção não capturada em fluxo crítico).

### Quando ele NEGA

> Se o código for **possivelmente perigoso** — houver risco real de quebra de lógica ou falha do sistema — o veredito é ❌ REPROVADO e o código **deve ser refeito**, apontando trecho a trecho o que compromete a estabilidade.

### Exemplos de reprovação automática

- Chamada à API sem `try/catch` em fluxo principal.
- Lógica que deixa o estado do app inconsistente (ex.: tarefa some da tela mas a exclusão falhou no servidor).
- Alteração que quebra um padrão estabelecido sem justificativa.

---

## 3️⃣ agent-cobertura 🧪

**Papel:** guardião da cobertura de testes das ações do usuário.

### O que ele valida em toda alteração

- **Ação nova = teste novo** — sempre que a demanda CRIA uma ação do usuário (botão, gesto, campo, fluxo de tela ou endpoint acionado pelo usuário), deve existir um teste na pasta `test/` que exercite essa ação.
- **Ação alterada = teste atualizado** — sempre que a demanda ALTERA o comportamento de uma ação existente, o teste correspondente deve ser atualizado (ou criado, caso ainda não exista).
- **Teste de verdade** — o teste executa a ação e verifica o efeito esperado; teste que só monta a tela (ou só chama o endpoint) sem verificar o resultado não conta.
- **Lugar certo** — todo teste vive na pasta `test/` do repositório, seguindo o padrão do projeto.

### Quando ele NEGA

> Se qualquer ação do usuário criada ou alterada na demanda estiver **sem teste correspondente** na pasta `test/`, o veredito é ❌ REPROVADO, listando ação por ação o que ficou descoberto.

### Exemplos de reprovação automática

- Botão, gesto ou endpoint novo sem teste que dispare a ação e verifique o resultado.
- Mudança no comportamento de uma ação sem atualizar o teste que a cobria.
- Teste criado fora da pasta `test/`.
- Teste que não exercita a ação (renderiza e não interage, ou não faz asserção).

---

## 4️⃣ agent-teste-real 🎯 (agente PRINCIPAL)

**Papel:** o veredito final. Simula o uso real do aplicativo e decide se a alteração **quebraria a produção**.

### O que ele faz em toda alteração

Cria e executa um **cenário de fluxo comum** de ponta a ponta, como um usuário de verdade:

```
CENÁRIO PADRÃO (executado a cada demanda):
 1. Registrar um usuário novo
 2. Fazer login e receber o token
 3. CRIAR uma tarefa            → deve aparecer na listagem
 4. EDITAR essa tarefa          → título/descrição/status atualizados
 5. Marcar como concluída       → estado persiste após recarregar
 6. EXCLUIR a tarefa            → some da listagem e retorna 404 no detalhe
 7. Fazer logout                → token invalidado, requisição seguinte falha
```

O cenário deve rodar contra o código **como ele ficará em produção** (servidor de verdade rodando, app consumindo a API real — não apenas testes unitários isolados). Quando a demanda tocar um fluxo específico, o agente **estende o cenário** para cobrir também esse fluxo.

### Quando ele NEGA

> Se **qualquer passo do cenário quebrar** — erro 500, resposta errada, dado que não persiste, app que trava — a alteração **não passa**: veredito ❌ REPROVADO com o passo exato que falhou, a saída do erro e a instrução de **recriar** a solução.

### Exemplos de reprovação automática

- Qualquer passo do cenário padrão retornando erro.
- Migração pendente que derrubaria o servidor em produção.
- Fluxo de criação/edição/exclusão funcionando "no teste unitário" mas falhando no fluxo real.

---

## Resumo

| Agente | Foco | Nega quando... |
|---|---|---|
| 🔐 `agent-security` | Endpoints, injeção, roubo de dados, infraestrutura | A alteração abre brecha de segurança ou afeta a infraestrutura |
| 🧹 `agent-qualidade` | Consistência, qualidade, robustez lógica | Há risco de quebra de lógica ou falha do sistema |
| 🧪 `agent-cobertura` | Toda ação do usuário tem teste na pasta `test/` | Há ação de usuário criada/alterada sem teste que a exercite |
| 🎯 `agent-teste-real` | Fluxo real: criar, editar, excluir tarefas | O cenário de produção quebra em qualquer passo |

**Lema do pipeline:** *nada entra no projeto sem passar pelos quatro — e o teste real dá a palavra final.*
