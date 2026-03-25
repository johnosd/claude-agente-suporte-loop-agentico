# Claude Agente de Suporte — Loop Agêntico

Projeto de estudo que implementa um agente de atendimento ao cliente com loop agêntico usando a API do Claude (Anthropic). O agente interpreta mensagens do usuário, decide quais ferramentas usar e executa ações de suporte de forma autônoma até concluir a tarefa.

## Como funciona

O loop agêntico segue este fluxo:

```
Mensagem do usuário
        ↓
   Claude analisa
        ↓
  stop_reason == "tool_use"? ──→ Executa a ferramenta ──→ Envia resultado ao Claude
        ↓ (não)
  stop_reason == "end_turn"
        ↓
   Resposta final
```

A cada iteração, o histórico completo de mensagens (incluindo os resultados das ferramentas) é enviado de volta ao Claude até ele concluir o atendimento.

## Ferramentas disponíveis

| Ferramenta | Descrição |
|---|---|
| `get_customer` | Busca informações de um cliente pelo ID (nome, email, status) |
| `lookup_order` | Busca dados de um pedido pelo número (produto, valor, status de entrega) |
| `process_refund` | Processa um reembolso para um pedido |

Os dados são simulados com dicionários em memória (`app/agent.py`).

## Instalação

```bash
# Clone o repositório
git clone <url-do-repositorio>
cd claude-agente-suporte-loop-agentico

# Crie e ative o ambiente virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Instale as dependências
pip install -r requirements.txt
```

Crie um arquivo `.env` na raiz com sua chave da API:

```
ANTHROPIC_API_KEY=sk-ant-...
```

## Uso

```bash
# Executar os cenários de teste embutidos
python app/agent.py

# Executar os testes
pytest
```

Saída esperada ao rodar `app/agent.py`:

```
--- TESTE 1 ---
O cliente ID-456 (Maria) está com status bloqueado...

--- TESTE 2 ---
O pedido 123456 corresponde a um Smartphone no valor de R$ 1500...

--- TESTE 3 ---
O reembolso de R$ 1500 para o pedido 123456 foi processado com sucesso...
```

## Estrutura

```
app/
└── agent.py       # Loop agêntico, definição das ferramentas e funções mock
tests/
└── test_agent.py  # Testes do agente
requirements.txt
```
