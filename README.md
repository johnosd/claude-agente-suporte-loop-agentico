# Claude Agente de Suporte - Loop Agentico

Projeto de estudo para a certificacao **Claude Certified Architect - Foundations**.

O repositorio implementa um agente de suporte ao cliente com ferramentas, loop agentico e regras deterministicas para controlar operacoes sensiveis como reembolso.

## Objetivo do projeto

O fluxo principal e:

1. receber a mensagem do usuario;
2. enviar o historico ao modelo Claude;
3. executar ferramentas quando o modelo retornar `stop_reason == "tool_use"`;
4. aplicar validacoes de negocio antes da execucao real;
5. devolver `tool_result` ao modelo;
6. repetir o ciclo ate `stop_reason == "end_turn"`.

## Arquitetura atual

O codigo relevante esta concentrado em [app/agent.py](c:\Users\johns\Documents\Projetos\Claude Code Pratice\claude_certified\claude-agente-suporte-loop-agentico\app\agent.py).

- `run_agent()`: orquestra o loop, monta o historico e chama a API da Anthropic.
- `execute_tool()`: roteia chamadas de ferramenta e aplica gates de negocio.
- `pre_tool_hook()`: bloqueia reembolsos acima de `500` antes da execucao da ferramenta.
- `get_customer_info()`: consulta mockada de clientes.
- `get_order_info()`: consulta mockada de pedidos.
- `process_refund()`: simulacao de reembolso.

As ferramentas expostas ao modelo sao:

| Ferramenta | Funcao |
|---|---|
| `get_customer` | Busca dados do cliente pelo ID |
| `lookup_order` | Busca dados do pedido |
| `process_refund` | Processa reembolso |

## Regras de negocio implementadas

- `process_refund` so deve seguir apos verificacao do cliente.
- Cliente com status `bloqueado` nao pode receber reembolso.
- `pre_tool_hook()` bloqueia qualquer reembolso acima de `500`.
- Erros retornam um objeto estruturado com `errorCategory`, `isRetryable`, `message` e `action`.

Exemplo de erro estruturado:

```python
{
    "errorCategory": "validation",
    "isRetryable": False,
    "message": "Cliente ID-999 nao encontrado",
    "action": "Informe ao usuario que o cliente nao foi encontrado..."
}
```

## Comportamento observado na revisao

Durante a revisao do codigo e dos testes, estes pontos ficaram claros:

- O prompt de sistema existe em `SYSTEM_PROMPT`, mas `run_agent()` so o usa quando o chamador passa `system=...`.
- O hook de valor roda antes da logica de verificacao do cliente, entao qualquer reembolso acima de `500` e bloqueado imediatamente.
- O caminho de sucesso real hoje exige cliente valido, cliente ativo e valor de reembolso menor ou igual a `500`.
- A simulacao de `process_refund()` so reconhece o pedido `123456`.
- A resposta mockada de `process_refund()` para sucesso devolve `amount: 3000`, independentemente do valor solicitado. Isso e uma limitacao atual do mock.
- O repositorio possui testes em [tests/test_agent.py](c:\Users\johns\Documents\Projetos\Claude Code Pratice\claude_certified\claude-agente-suporte-loop-agentico\tests\test_agent.py), mas `pytest` nao esta listado em [requirements.txt](c:\Users\johns\Documents\Projetos\Claude Code Pratice\claude_certified\claude-agente-suporte-loop-agentico\requirements.txt).

## Estrutura do projeto

```text
app/
  agent.py
tests/
  test_agent.py
requirements.txt
setup_env.sh
README.md
```

## Requisitos

- Python 3.10+
- chave `ANTHROPIC_API_KEY`

Dependencias atuais do projeto:

```text
anthropic==0.84.0
python-dotenv
```

Para rodar os testes deste repositorio, instale tambem:

```bash
pip install pytest
```

## Instalacao

```bash
git clone <url-do-repositorio>
cd claude-agente-suporte-loop-agentico
python -m venv venv
```

Ativacao da virtualenv:

- Linux/macOS: `source venv/bin/activate`
- Windows PowerShell: `.\venv\Scripts\Activate.ps1`

Instale as dependencias:

```bash
pip install -r requirements.txt
pip install pytest
```

Crie um arquivo `.env` na raiz:

```env
ANTHROPIC_API_KEY=sk-ant-...
```

Opcionalmente, use o script [setup_env.sh](c:\Users\johns\Documents\Projetos\Claude Code Pratice\claude_certified\claude-agente-suporte-loop-agentico\setup_env.sh) em ambientes Unix-like para recriar a virtualenv e instalar dependencias.

## Execucao

Executar o script principal:

```bash
python app/agent.py
```

O bloco `__main__` roda alguns cenarios de exemplo e passa `system=SYSTEM_PROMPT`.

Se quiser usar `run_agent()` diretamente, passe o prompt de sistema explicitamente para manter o comportamento esperado:

```python
from app.agent import run_agent, SYSTEM_PROMPT

run_agent(
    "Sou o Joao ID-123, quero reembolso de 200 do pedido 123456",
    system=SYSTEM_PROMPT,
)
```

## Testes

Suite atual:

- [tests/test_agent.py](c:\Users\johns\Documents\Projetos\Claude Code Pratice\claude_certified\claude-agente-suporte-loop-agentico\tests\test_agent.py)

Execucao:

```bash
pytest -q tests
```

Observacao importante: no ambiente revisado, `pytest` nao estava instalado nem no Python global nem na `venv`, entao a suite nao pode ser executada sem instalar essa dependencia antes.

## Cenarios coerentes com o codigo atual

| Cenario | Entrada | Resultado esperado pelo codigo |
|---|---|---|
| Reembolso sem verificacao | `Processe reembolso de 200 para o pedido 123456` | bloqueio por cliente nao verificado |
| Cliente bloqueado | `Sou a Maria ID-456, quero reembolso de 200 do pedido 123456` | bloqueio por regra de negocio |
| Valor acima do limite | `Sou o Joao ID-123, quero reembolso de 1500 do pedido 123456` | bloqueio no `pre_tool_hook()` |
| Fluxo permitido | `Sou o Joao ID-123, quero reembolso de 200 do pedido 123456` | tentativa de processamento com mock de sucesso |

## Observacoes de manutencao

- Ha sinais de problema de encoding em arquivos textuais exibidos no terminal atual.
- Os testes documentam intencoes do fluxo, mas pelo menos um deles parece divergir da implementacao atual do hook de valor.
- Se a intencao for usar este repositorio como referencia de arquitetura, vale alinhar mocks, testes e README antes de expandir o projeto.
