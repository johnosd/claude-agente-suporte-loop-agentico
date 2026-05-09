# Claude Agente de Suporte - Loop Agentico

Implementa um agente de suporte ao cliente com loop agentico, ferramentas, validacoes deterministicas, backoff com retry e escalacao para humanos.

---

## Implementacoes por etapa

| Etapa | Conceito | Task Statement |
|-------|----------|----------------|
| 1 | Loop agentico com `stop_reason` | 1.1 |
| 2 | Ferramentas com descricoes diferenciadas | 2.1 |
| 3 | Erros estruturados + prerequisite gate | 1.4, 2.2 |
| 4 | PreToolUse hook por threshold | 1.5 |
| 5 | Escalacao com handoff estruturado | 1.4 |
| 5.5 | Exponential backoff com jitter | 2.2 |

---

## Etapa 1 — Loop agentico com `stop_reason`

`run_agent()` em [app/agent.py](app/agent.py) implementa o ciclo:

1. Envia a mensagem do usuario ao modelo Claude com as definicoes de ferramentas.
2. Verifica `response.stop_reason`:
   - `"end_turn"` → extrai o texto e retorna.
   - `"tool_use"` → executa as ferramentas solicitadas, adiciona os resultados ao historico e volta ao passo 1.

```python
while True:
    response = client.messages.create(**params, messages=messages)

    if response.stop_reason == "end_turn":
        return response

    elif response.stop_reason == "tool_use":
        # executa ferramentas e adiciona tool_results ao historico
        ...
```

---

## Etapa 2 — Ferramentas com descricoes diferenciadas

Cada ferramenta tem uma descricao estruturada com tres secoes para guiar o modelo na escolha correta:

- **Use:** quando usar a ferramenta
- **Nao use:** casos em que ela nao deve ser chamada
- **Exemplo:** exemplo de pedido do usuario que aciona a ferramenta

```python
{
    "name": "get_customer",
    "description": """Use: para obter informacoes do cliente como nome, status, email
                        Nao use: para buscar pedidos ou executar acoes
                        Exemplo: qual status do cliente ID-456""",
    ...
}
```

As quatro ferramentas expostas ao modelo:

| Ferramenta | Funcao |
|------------|--------|
| `get_customer` | Busca dados do cliente pelo ID |
| `lookup_order` | Busca dados do pedido |
| `process_refund` | Processa reembolso |
| `escalate_to_human` | Escala o caso para um agente humano |

---

## Etapa 3 — Erros estruturados + prerequisite gate

### Erros estruturados

Todas as funcoes de ferramenta retornam um objeto padronizado em caso de falha, com quatro campos que o modelo usa para decidir o proximo passo:

```python
{
    "errorCategory": "validation" | "business" | "transient",
    "isRetryable": True | False,
    "message": "descricao do erro",
    "action": "instrucao para o modelo sobre o que fazer"
}
```

Categorias:

| Categoria | Significado | Retentavel |
|-----------|-------------|------------|
| `validation` | ID nao existe, dado invalido | Nao |
| `business` | Regra de negocio violada (cliente bloqueado, limite excedido) | Nao |
| `transient` | Falha temporaria de infraestrutura | Sim (ver Etapa 5.5) |

### Prerequisite gate

`execute_tool()` em [app/agent.py](app/agent.py) bloqueia `process_refund` se o cliente ainda nao foi verificado nessa sessao:

```python
if tool_name == "process_refund":
    if not client_verification:
        return {
            "errorCategory": "validation",
            "isRetryable": False,
            "message": "Cliente nao verificado. ...",
            ...
        }
    elif verified_customer_data.get("status") == "bloqueado":
        return {
            "errorCategory": "business",
            ...
        }
```

O estado de verificacao e mantido em variaveis locais de `run_agent()` e atualizado apos um `get_customer` bem-sucedido:

```python
if block.name == "get_customer" and "errorCategory" not in result:
    client_verification = True
    verified_customer_data = result
```

---

## Etapa 4 — PreToolUse hook por threshold

`pre_tool_hook()` e chamado dentro de `execute_tool()` antes de qualquer ferramenta rodar. Bloqueia reembolsos acima de `500`:

```python
def pre_tool_hook(tool_name: str, tool_input: dict) -> dict | None:
    amount = tool_input.get("amount")
    if tool_name == "process_refund" and amount > 500:
        return {
            "errorCategory": "business",
            "isRetryable": False,
            "message": f"Valor do reembolso {amount} excede o limite permitido de 500.",
            "action": "Informe ao usuario que o valor excede o limite e sugira escalar para suporte."
        }
    return None
```

Se o hook retornar um objeto, `execute_tool()` retorna esse objeto imediatamente sem executar a ferramenta real. O modelo recebe o erro e decide escalar ou informar o usuario.

---

## Etapa 5 — Escalacao com handoff estruturado

A ferramenta `escalate_to_human` aceita um payload rico para que o agente humano receba contexto completo sem precisar reler o historico:

```python
{
    "name": "escalate_to_human",
    "input_schema": {
        "properties": {
            "customer_id":        {"type": "string"},
            "customer_name":      {"type": "string"},
            "customer_status":    {"type": "string"},
            "order_number":       {"type": "string"},
            "amount":             {"type": "number"},
            "root_cause":         {"type": "string"},
            "recommended_action": {"type": "string"}
        },
        "required": ["customer_id", "root_cause", "recommended_action"]
    }
}
```

Situacoes em que o modelo deve acionar a escalacao (descritas na descricao da ferramenta):
- cliente bloqueado
- valor acima do limite
- politica ambigua
- cliente solicita explicitamente falar com humano

A implementacao imprime o handoff e retorna um `ticket_id`:

```python
def escalate_to_human(handoff_data: dict) -> dict:
    # imprime resumo para a fila humana
    return {"status": "escalated", "ticket_id": "TKT-001", ...}
```

---

## Etapa 5.5 — Exponential backoff com jitter

`execute_tool_with_retry()` envolve `execute_tool()` e reexecuta apenas quando o resultado e um erro `transient` com `isRetryable == True`:

```python
def execute_tool_with_retry(tool_name, tool_input, ..., max_retries=3):
    for attempt in range(max_retries):
        result = execute_tool(...)

        if not (result.get("errorCategory") == "transient" and result.get("isRetryable")):
            return result  # sucesso ou erro nao retentavel

        if attempt < max_retries - 1:
            wait = 2 ** attempt + random.uniform(0, 1)  # 1s, 2s, 4s + jitter
            time.sleep(wait)

    return {"errorCategory": "transient", "isRetryable": False, "message": "Servico indisponivel apos 3 tentativas", ...}
```

Apos esgotar as tentativas, retorna um erro `transient` com `isRetryable: False` para que o modelo escale para humano.

---

## Fluxo completo por cenario

| Cenario | Caminho | Resultado |
|---------|---------|-----------|
| Reembolso sem verificar cliente | `process_refund` → gate bloqueia | erro `validation` |
| Cliente bloqueado | `get_customer` → gate de status | erro `business` |
| Valor acima de 500 | `process_refund` → `pre_tool_hook` | erro `business` |
| Servico de pedidos indisponivel | `lookup_order` → backoff x3 | erro `transient` → escalacao |
| Fluxo de sucesso | `get_customer` → `lookup_order` → `process_refund` | reembolso processado |

---

## Estrutura do projeto

```text
app/
  agent.py          # loop, ferramentas, gates, hook, backoff, escalacao
tests/
  test_agent.py     # testes unitarios com mock da API
requirements.txt
CLAUDE.md
README.md
```

---

## Requisitos

- Python 3.10+
- `ANTHROPIC_API_KEY` no arquivo `.env`

```text
anthropic==0.84.0
python-dotenv
```

---

## Instalacao

```bash
git clone <url-do-repositorio>
cd claude-agente-suporte-loop-agentico
python -m venv venv
```

Ativacao:

- Linux/macOS: `source venv/bin/activate`
- Windows PowerShell: `.\venv\Scripts\Activate.ps1`

```bash
pip install -r requirements.txt
pip install pytest
```

Crie `.env` na raiz:

```env
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Execucao

```bash
python app/agent.py
```

O bloco `__main__` roda o cenario ativo (backoff por padrao). Para outros cenarios, descomente as linhas correspondentes no final de [app/agent.py](app/agent.py).

Para usar `run_agent()` diretamente:

```python
from app.agent import run_agent, SYSTEM_PROMPT

run_agent(
    "Sou o Joao ID-123, quero reembolso de 200 do pedido 123456",
    system=SYSTEM_PROMPT,
)
```

---

## Testes

```bash
pytest -q tests
```

Cobertura atual em [tests/test_agent.py](tests/test_agent.py):

| Teste | Cenario |
|-------|---------|
| `test_a_refund_sem_cliente_verificado` | prerequisite gate bloqueia `process_refund` |
| `test_b_cliente_bloqueado` | gate de status devolve erro `business` |
| `test_c_reembolso_sucesso` | fluxo completo com cliente ativo e valor valido |
