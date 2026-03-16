def test_get_response():
    # Simula uma resposta do cliente
    response = {
        "id": "msg_013Zva2CMHLNnXjNJJKqJ2EF",
        "container": {
            "id": "id",
            "expires_at": "2019-12-27T18:11:19.117Z"
        },
        "content": [
            {
            "citations": [
                {
                "cited_text": "cited_text",
                "document_index": 0,
                "document_title": "document_title",
                "end_char_index": 0,
                "file_id": "file_id",
                "start_char_index": 0,
                "type": "char_location"
                }
            ],
            "text": "Hi! My name is Claude.",
            "type": "text"
            }
        ],
        "model": "claude-opus-4-6",
        "role": "assistant",
        "stop_reason": "end_turn",
        "stop_sequence": "",
        "type": "message",
        "usage": {
            "cache_creation": {
            "ephemeral_1h_input_tokens": 0,
            "ephemeral_5m_input_tokens": 0
            },
            "cache_creation_input_tokens": 2051,
            "cache_read_input_tokens": 2051,
            "inference_geo": "inference_geo",
            "input_tokens": 2095,
            "output_tokens": 503,
            "server_tool_use": {
            "web_fetch_requests": 2,
            "web_search_requests": 0
            },
            "service_tier": "standard"
        }
        }

    # Verifica se a resposta é processada corretamente
    print(response["stop_reason"] )

    print(response["content"][0]["text"])
    # assert response["stop_reason"] == "end_turn"
    # assert response["choices"][0]["message"]["content"] == "O status do cliente ID-123 é ativo."

