# Claude Agente de Suporte — Loop Agêntico

Projeto de estudo para a certificação **Claude Certified Architect – Foundations**.
Implementa um agente de atendimento ao cliente com loop agêntico usando a API do Claude (Anthropic).

O agente interpreta mensagens do usuário, decide quais ferramentas usar, aplica regras de negócio
e executa ações de suporte de forma autônoma até concluir a tarefa ou escalar para um humano.

---

## Como funciona

```
Mensagem do usuário
        ↓
   Claude analisa
        ↓
stop_reason == "tool_use"?
        ↓ sim
  pre_tool_hook()          → bloqueia se violar regra de negócio (ex: valor > R$500)
        ↓ passou
  execute_tool()           → roteia para a ferramenta correta
        ↓
  prerequisite gate        → bloqueia process_refund se cliente não verificado
        ↓
  envia tool_result        → histórico atualizado, nova iteração
        ↓
stop_reason == "end_turn"
        ↓
   Resposta final ao usuário
```

A cada iteração, o histórico completo de mensagens é enviado ao Claude.
Claude pode chamar múltiplas ferramentas em paralelo numa única iteração.

---

## Arquitetura do código

```
run_agent()        — orquestração pura: loop, stop_reason, histórico de mensagens
execute_tool()     — roteamento e execução das ferramentas com regras de negócio
pre_tool_hook()    — interceptação antes da execução (compliance determinístico)
get_customer_info()  — simula consulta ao banco de clientes
get_order_info()     — simula consulta ao banco de pedidos
process_refund()     — simula processamento de reembolso
```

---

## Ferramentas disponíveis

| Ferramenta | Quando usar | Não usar para |
|---|---|---|
| `get_customer` | Buscar nome, email, status do cliente por ID | Pedidos ou ações |
| `lookup_order` | Buscar produto, valor, status de entrega por número do pedido | Dados do cliente |
| `process_refund` | Executar reembolso (exige cliente verificado) | Consultas |

Os dados são simulados com dicionários em memória (`app/agent.py`).

---

## Regras de negócio implementadas

- **Prerequisite gate:** `process_refund` só executa após `get_customer` retornar cliente válido
- **Bloqueio por status:** clientes com status `bloqueado` não podem receber reembolso
- **Limite por valor:** reembolsos acima de R$500 são bloqueados pelo hook e redirecionados para suporte
- **Erros estruturados:** todas as ferramentas retornam `errorCategory`, `isRetryable`, `message` e `action`

---

## Erros estruturados

Quando uma operação falha, as ferramentas retornam um dict estruturado:

```python
{
    "errorCategory": "validation" | "business" | "permission" | "transient",
    "isRetryable": False,
    "message": "Descrição legível do erro",
    "action": "O que Claude deve fazer a seguir"
}
```

Isso permite que Claude tome decisões de recuperação adequadas em vez de travar.

---

## Instalação

```bash
git clone <url-do-repositorio>
cd claude-agente-suporte-loop-agentico

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

Crie um arquivo `.env` na raiz:

```
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Uso

```bash
python app/agent.py
pytest
```

---

## Cenários de teste

| Teste | Mensagem | Resultado esperado |
|---|---|---|
| A | "Processe reembolso de 1500 para o pedido 123456" | Hook bloqueia: valor > R$500 |
| B | "Sou a Maria ID-456, quero reembolso de 1500 do pedido 123456" | Gate bloqueia: cliente bloqueado |
| C | "Sou o João ID-123, quero reembolso de 1500 do pedido 123456" | Hook bloqueia: valor > R$500 |
| Hook A | "Sou o João ID-123, quero reembolso de 1500 do pedido 123456" | Bloqueado por threshold |
| Hook B | "Sou o João ID-123, quero reembolso de 200 do pedido 123456" | Reembolso processado ✅ |

---

## Estrutura

```
app/
└── agent.py       # Loop agêntico, ferramentas, hooks e regras de negócio
tests/
└── test_agent.py  # Testes automatizados
requirements.txt
.env               # Não commitado — contém ANTHROPIC_API_KEY
```

---

## Conceitos praticados (Claude Certified Architect)

| Task Statement | Conceito |
|---|---|
| 1.1 | Loop agêntico com `stop_reason` ("tool_use" vs "end_turn") |
| 1.4 | Prerequisite gates vs prompt instructions para compliance crítico |
| 1.5 | PreToolUse hooks para garantias determinísticas |
| 2.1 | Descrições de ferramentas diferenciadas para seleção confiável |
| 2.2 | Erros estruturados com categoria, retryable e action |
