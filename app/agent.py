import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic()

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
            "isRetriable": False,
            "message": f"Cliente {customer_id} não encontrado",
            "action": "Informe ao usuário que o cliente não foi encontrado e sugira verificar o ID do cliente ou entrar em contato com o suporte."
        }
    return result

def get_order_info(order_number: str) -> dict:
    # Simula uma consulta a um banco de dados ou API externa
    banco_fake = {
        "123456": {"produto": "Smartphone", "valor": 1500, "status_entrega": "entregue"},
        "654321": {"produto": "Notebook", "valor": 3000, "status_entrega": "em trânsito"},
    }
    result = banco_fake.get(order_number)

    if result is None:
        return {
            "errorCategory": "validation",
            "isRetriable": False,
            "message": f"Pedido {order_number} não encontrado",
            "action": "Informe ao usuário que o pedido não foi encontrado e sugira verificar o número do pedido ou entrar em contato com o suporte."
        }
    
    return result

def process_refund(order_number: str, amount: float) -> dict:
    # Simula o processamento de um reembolso
    banco_fake = {
        "123456": {"status": "reembolso processado", "order_number": "123456", "amount": 3000},
    }
    
    result = banco_fake.get(order_number)

    return banco_fake.get(order_number, {
        "errorCategory": "business",
        "isRetriable": False,
        "message": f"Pedido {order_number} não encontrado",
        "action": "Informe ao usuário que o pedido não foi encontrado e sugira verificar o número do pedido ou entrar em contato com o suporte."
    })

def run_agent(user_message: str):
    messages = [{"role": "user", "content": user_message}]

    while True:
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens =1024,
            tools=tools,
            messages=messages
        )

        # SEU CÓDIGO AQUI:
        # 1. verificar response.stop_reason
        # 2. se "end_turn" → imprimir resposta e retornar
        if response.stop_reason == "end_turn":
            print(response.content[0].text)
            return response
        # 3. se "tool_use" → extrair o tool call, executar, adicionar resultado
        elif response.stop_reason == "tool_use":
            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input   # já é um dict
                    tool_use_id = block.id     # você vai precisar disso
            
            messages.append({
                "role": "assistant",
                "content": response.content  # passa a lista inteira de blocos
            })

            if tool_name == "get_customer":
                result = get_customer_info(tool_input["customer_id"])
            elif tool_name == "lookup_order":
                result = get_order_info(tool_input["order_number"])
            elif tool_name == "process_refund":
                result = process_refund(tool_input["order_number"], tool_input["amount"])

            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,  # liga ao tool_use correto
                        "content": str(result)  # resultado como string
                    }
                ]
            })

            

if __name__ == "__main__":
    print("--- TESTE 1 ---")
    run_agent("Qual o status do cliente ID-456?")
    
    print("--- TESTE 2 ---")
    run_agent("Qual o produto do pedido 123456?")
    
    print("--- TESTE 3 ---")
    run_agent("Processe um reembolso de 1500 reais para o pedido 123456")