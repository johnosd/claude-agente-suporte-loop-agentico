import pytest
from unittest.mock import patch, MagicMock
from app.agent import run_agent


def _block(type_, **kwargs):
    b = MagicMock()
    b.type = type_
    for k, v in kwargs.items():
        setattr(b, k, v)
    return b


def _response(stop_reason, content):
    r = MagicMock()
    r.stop_reason = stop_reason
    r.content = content
    return r


def _tool_results(call_args_list, call_index):
    """Retorna a lista de tool_results enviada na chamada de índice call_index."""
    return call_args_list[call_index].kwargs["messages"][-1]["content"]


# ─── TESTE A ──────────────────────────────────────────────────────────────────
# Fluxo: process_refund sem get_customer → gate bloqueia → erro validação
# Iterações: 2  (1 tool_use + 1 end_turn)

def test_a_refund_sem_cliente_verificado():
    r1 = _response("tool_use", [
        _block("tool_use", id="t1", name="process_refund",
               input={"order_number": "123456", "amount": 1500}),
    ])
    r2 = _response("end_turn", [
        _block("text", text="Cliente não verificado. Não é possível processar o reembolso."),
    ])

    with patch("app.agent.client.messages.create", side_effect=[r1, r2]) as mock:
        run_agent("Processe reembolso de 1500 para o pedido 123456")

    assert mock.call_count == 2

    results = _tool_results(mock.call_args_list, 1)
    refund_result = next(r for r in results if r["tool_use_id"] == "t1")
    assert "validation" in refund_result["content"]


# ─── TESTE B ──────────────────────────────────────────────────────────────────
# Fluxo: get_customer (Maria bloqueada) + lookup_order paralelo → process_refund → erro business
# Iterações: 3  (2 tool_use + 1 end_turn)

def test_b_cliente_bloqueado():
    r1 = _response("tool_use", [
        _block("tool_use", id="t1", name="get_customer",  input={"customer_id": "ID-456"}),
        _block("tool_use", id="t2", name="lookup_order",  input={"order_number": "123456"}),
    ])
    r2 = _response("tool_use", [
        _block("tool_use", id="t3", name="process_refund",
               input={"order_number": "123456", "amount": 1500}),
    ])
    r3 = _response("end_turn", [
        _block("text", text="Cliente bloqueado. Reembolso não autorizado."),
    ])

    with patch("app.agent.client.messages.create", side_effect=[r1, r2, r3]) as mock:
        run_agent("Sou a Maria ID-456, quero reembolso de 1500 do pedido 123456")

    assert mock.call_count == 3

    results = _tool_results(mock.call_args_list, 2)
    refund_result = next(r for r in results if r["tool_use_id"] == "t3")
    assert "business" in refund_result["content"]


# ─── TESTE C ──────────────────────────────────────────────────────────────────
# Fluxo: get_customer (João ativo) + lookup_order + process_refund paralelo → sucesso
# Iterações: 2  (1 tool_use com 3 ferramentas + 1 end_turn)

def test_c_reembolso_sucesso():
    r1 = _response("tool_use", [
        _block("tool_use", id="t1", name="get_customer",  input={"customer_id": "ID-123"}),
        _block("tool_use", id="t2", name="lookup_order",  input={"order_number": "123456"}),
        _block("tool_use", id="t3", name="process_refund",
               input={"order_number": "123456", "amount": 1500}),
    ])
    r2 = _response("end_turn", [
        _block("text", text="Reembolso de R$1500 processado com sucesso para o pedido 123456."),
    ])

    with patch("app.agent.client.messages.create", side_effect=[r1, r2]) as mock:
        run_agent("Sou o João ID-123, quero reembolso de 1500 do pedido 123456")

    assert mock.call_count == 2

    results = _tool_results(mock.call_args_list, 1)
    refund_result = next(r for r in results if r["tool_use_id"] == "t3")
    assert "reembolso processado" in refund_result["content"]
