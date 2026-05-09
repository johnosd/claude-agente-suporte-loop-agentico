import anthropic
import random
import time 
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic()

SYSTEM_PROMPT = """Você é um agente de suporte ao cliente especializado.
Sempre verifique a identidade do cliente antes de processar reembolsos.
Seja educado, conciso e proativo em resolver os problemas do cliente."""

tools = [
    {
        "name": "get_customer",
        "description": """Use: para obter informações do cliente como nome, status email
                            Não use: para buscar pedidos ou executar ações
                            Exemplo:  qual status do cliente ID-456""",  # sua descrição aqui
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer's ID to look up in format ID-123"
                }
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "lookup_order",
        "description": """Use: para obter informações de um pedido como produto, valor, status da entrega
                            Não use: para buscar clientes ou executar ações
                            Exemplo:  qual produto do numero do pedido 123456""",  # sua descrição aqui
        "input_schema": {
            "type": "object",
            "properties": {
                "order_number": {
                    "type": "string",
                    "description": "Customer's order number to look up"
                }
            },
            "required": ["order_number"]
        }
    },
    {
        "name": "process_refund",
        "description": """Use: para executar uma ação de reembolso
            Não use: para buscar clientes ou pedidos
            Exemplo:  reembolse o valor de x do pedido 123456""",  # sua descrição aqui
        "input_schema": {
            "type": "object",
            "properties": {
                "order_number": {
                    "type": "string",
                    "description": "Customer's order number to process refund for"
                },
                "amount": {
                    "type": "number",
                    "description": "Amount to refund"
                }
            },
            "required": ["order_number", "amount"]
        }
    },
    {
    "name": "escalate_to_human",
    "description": """Use: quando não for possível resolver o caso automaticamente.
                    Situações: cliente bloqueado, valor acima do limite, política ambígua, 
                    cliente solicita explicitamente falar com humano.
                    Não use: para casos que o agente consegue resolver autonomamente.
                    Preencha todos os campos disponíveis para contexto completo ao agente humano.""",  # você escreve
    "input_schema": {
        "type": "object",
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
]

def get_customer_info(customer_id: str) -> dict:
    # Simula uma consulta a um banco de dados ou API externa
    banco_fake = {
        "ID-123": {"nome": "João", "status": "ativo", "email": "joao@email.com"},
        "ID-456": {"nome": "Maria", "status": "bloqueado", "email": "maria@email.com"},
    }
    result =  banco_fake.get(customer_id)
    
    if result is None:
        return {
            "errorCategory": "validation",
            "isRetryable": False,
            "message": f"Cliente {customer_id} não encontrado",
            "action": "Informe ao usuário que o cliente não foi encontrado e sugira verificar o ID do cliente ou entrar em contato com o suporte."
        }
    return result

def get_order_info(order_number: str) -> dict:
    # Simula uma consulta a um banco de dados ou API externa
    if random.random() < 0.4:  # Simula uma falha temporária com 10% de chance
        return {
            "errorCategory": "transient",
            "isRetryable": True,
            "message": f"Falha temporária ao buscar informações do pedido {order_number}",
            "action": "Tente novamente em alguns instantes."
        }
    
    banco_fake = {
        "123456": {"produto": "Smartphone", "valor": 1500, "status_entrega": "entregue"},
        "654321": {"produto": "Notebook", "valor": 3000, "status_entrega": "em trânsito"},
    }
    result = banco_fake.get(order_number)

    if result is None:
        return {
            "errorCategory": "validation",
            "isRetryable": False,
            "message": f"Pedido {order_number} não encontrado",
            "action": "Informe ao usuário que o pedido não foi encontrado e sugira verificar o número do pedido ou entrar em contato com o suporte."
        }
    
    return result

def process_refund(order_number: str, amount: float) -> dict:
    # Simula o processamento de um reembolso
    banco_fake = {
        "123456": {"status": "reembolso processado", "order_number": "123456", "amount": 3000},
    }
    
    # result = banco_fake.get(order_number)

    return banco_fake.get(order_number, {
        "errorCategory": "business",
        "isRetryable": False,
        "message": f"Pedido {order_number} não encontrado",
        "action": "Informe ao usuário que o pedido não foi encontrado e sugira verificar o número do pedido ou entrar em contato com o suporte."
    })

def pre_tool_hook(tool_name: str, tool_input:dict) -> dict | None:
    # Exemplo de pré-validação para process_refund
    amount = tool_input.get("amount")
    if tool_name == "process_refund" and amount > 500:
        # retornar erro estruturado para o modelo, para modelo escalar para interacao humana.
            return {
                "errorCategory": "business",
                "isRetryable": False,
                "message": f"Valor do reembolso {amount} excede o limite permitido de 500.",
                "action": "Informe ao usuário que o valor do reembolso excede o limite permitido e sugira fornecer um valor menor ou entrar em contato com o suporte para casos especiais."
            }
    return None

def escalate_to_human(handoff_data: dict) -> dict:
    print("\n🚨 ESCALAÇÃO PARA HUMANO:")
    print(f"  Cliente:  {handoff_data.get('customer_name')} ({handoff_data.get('customer_id')})")
    print(f"  Motivo:   {handoff_data.get('root_cause')}")
    print(f"  Ação:     {handoff_data.get('recommended_action')}")

    return {
        "status": "escalated",
        "ticket_id": "TKT-001",
        "message": "O caso foi escalado para um agente humano."
    }

def execute_tool_with_retry(
        tool_name: str,
        tool_input: dict,
        client_verification: bool,
        verified_customer_data: dict | None,
        max_retries: int = 3
    ) -> dict:
    for attempt in range(max_retries):
        result = execute_tool(tool_name, tool_input, client_verification, verified_customer_data)
        
        # se não é erro transient retryable → retorna imediatamente
        if not (result.get("errorCategory") == "transient" and result.get("isRetryable") == True):
            return result
        
        # se é erro transient retryable → espera e tenta novamente
        if attempt < max_retries - 1:  # evita esperar após última tentativa
            wait = 2 ** attempt + random.uniform(0, 1)  # tempo de espera exponencial 2, 4, 8 segundos + jitter aleatório
            print(f"  ⏳ Tentativa {attempt + 1} falhou. Aguardando {wait}s...")
            time.sleep(wait)

    # esgotou tentativas → retorna erro para escalar
    return {
        "errorCategory": "transient",
        "isRetryable": False,
        "message": "Serviço indisponível após 3 tentativas",
        "action": "Escale para agente humano informando falha no serviço de pedidos"
    }

def execute_tool(
        tool_name: str, 
        tool_input: dict, 
        client_verification: bool, 
        verified_customer_data: dict | None 
        ) -> dict:
    
    hook_result = pre_tool_hook(tool_name, tool_input)

    if hook_result is not None:
        return hook_result

    if tool_name == "get_customer":
        return get_customer_info(tool_input["customer_id"])

    elif tool_name == "lookup_order":
        return get_order_info(tool_input["order_number"])

    elif tool_name == "process_refund":
        if not client_verification:
            return {
                "errorCategory": "validation",
                "isRetryable": False,
                "message": "Cliente não verificado. Por favor, verifique o cliente antes de processar o reembolso.",
                "action": "Informe ao usuário que o cliente precisa ser verificado antes de processar o reembolso e sugira verificar o status do cliente ou entrar em contato com o suporte."
                }
        elif verified_customer_data.get("status")== "bloqueado":
            return{
                "errorCategory": "business",
                "isRetryable": False,
                "message": "Cliente bloqueado. Não é possível processar o reembolso.",
                "action": "Informe ao usuário que o cliente está bloqueado e não é possível processar o reembolso. Sugira entrar em contato com o suporte para mais informações."
            }
        else:
            return process_refund(tool_input["order_number"], tool_input["amount"])
    
    elif tool_name == "escalate_to_human":
        return escalate_to_human(tool_input)

        
def add_user_message(messages, text):
    user_message = {"role": "user", "content": text}
    messages.append(user_message)

def add_assistant_message(messages, text):
    assistant_message = {"role": "assistant", "content": text}
    messages.append(assistant_message)

def run_agent(
    user_message: str,
    model: str = "claude-opus-4-5",
    max_tokens: int = 1024,
    temperature: float = 1.0,
    system: str = None,
):

    messages = []
    add_user_message(messages, user_message)

    client_verification = False
    verified_customer_data = None

    params = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "tools": tools,
    }
    if system:
        params["system"] = system

    while True:
        response = client.messages.create(**params, messages=messages)

        if response.stop_reason == "end_turn":
            print(response.content[0].text)
            return response

        elif response.stop_reason == "tool_use":
            add_assistant_message(messages, response.content)

            tool_results = []  # ← coleta todos os resultados

            for block in response.content:
                if block.type == "tool_use":
                    #result = execute_tool(
                    result = execute_tool_with_retry(
                        tool_name = block.name,
                        tool_input = block.input,
                        client_verification = client_verification,
                        verified_customer_data = verified_customer_data
                    )

                    # atualiza estado se get_custormer retornou cliente válido
                    if block.name == "get_customer" and "errorCategory" not in result:
                        client_verification = True
                        verified_customer_data = result

                    tool_results.append({   # ← adiciona ao invés de sobrescrever
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result)
                    })

            add_user_message(messages, tool_results)

            

if __name__ == "__main__":
    parameters = {
        "temperature": 1.0,
        "system": SYSTEM_PROMPT,
    }

    # print("--- TESTE A: reembolso sem verificar cliente primeiro ---")
    # run_agent("Processe reembolso de 1500 para o pedido 123456", **parameters)

    # print("--- TESTE B: cliente bloqueado tenta reembolso ---")
    # run_agent("Sou a Maria ID-456, quero reembolso de 1500 do pedido 123456", **parameters)

    # print("--- TESTE C: cliente ativo consegue reembolso ---")
    # run_agent("Sou o João ID-123, quero reembolso de 1500 do pedido 123456", **parameters)

    # # Hooks
    # print("--- TESTE HOOK A: reembolso acima de 500 (deve bloquear) ---")
    # run_agent("Sou o João ID-123, quero reembolso de 1500 do pedido 123456", **parameters)

    # print("--- TESTE HOOK B: reembolso abaixo de 500 (deve processar) ---")
    # run_agent("Sou o João ID-123, quero reembolso de 200 do pedido 123456", **parameters)

    # print("--- TESTE ESCALAÇÃO: cliente bloqueado ---")
    # run_agent("Sou a Maria ID-456, quero reembolso de 1500 do pedido 123456", **parameters)

    print("--- TESTE BACKOFF: busca pedido com falha transient ---")
    run_agent("Sou o João ID-123, quero saber o status do pedido 123456", **parameters)