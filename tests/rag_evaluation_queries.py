"""
Golden dataset for RAG pipeline evaluation.
Covers different query types to validate system quality.
"""

EVALUATION_QUERIES = [
    # --- FACTUAL ---
    {
        "id": "F01",
        "type": "factual",
        "query": "Quem é o Alexandre Ottoni?",
        "expected_topics": ["apresentador", "jovem nerd", "host"],
        "expected_episodes": ["NerdCast"],
        "notes": "Deve identificar o host principal do podcast",
    },
    {
        "id": "F02",
        "type": "factual",
        "query": "Quais astronautas participaram da missão Artemis II?",
        "expected_topics": ["Victor Glover", "Reed Wiseman", "Cristina", "Jeremy"],
        "expected_episodes": ["NerdCast 1026"],
        "notes": "Deve listar os 4 astronautas corretamente",
    },
    {
        "id": "F03",
        "type": "factual",
        "query": "O que é o programa Artemis da NASA?",
        "expected_topics": ["lua", "nasa", "missão tripulada", "exploração"],
        "expected_episodes": ["NerdCast 1026"],
        "notes": "Deve explicar o programa sem inventar datas ou detalhes",
    },

    # --- COMPARATIVA ---
    {
        "id": "C01",
        "type": "comparativa",
        "query": "Qual a diferença entre a Artemis I e a Artemis II?",
        "expected_topics": ["tripulada", "não tripulada", "teste"],
        "expected_episodes": ["NerdCast 1026"],
        "notes": "Deve distinguir corretamente as duas missões",
    },
    {
        "id": "C02",
        "type": "comparativa",
        "query": "Como o NerdCast compara exploração espacial com outros temas de ciência?",
        "expected_topics": ["ciência", "tecnologia", "espaço"],
        "expected_episodes": ["multiple"],
        "notes": "Teste de cross-episode — deve buscar em múltiplos episódios",
    },

    # --- RESUMO ---
    {
        "id": "R01",
        "type": "resumo",
        "query": "Sobre o que foi o episódio do NerdCast sobre Artemis II?",
        "expected_topics": ["lua", "astronautas", "nasa", "missão"],
        "expected_episodes": ["NerdCast 1026"],
        "notes": "Deve sintetizar os principais pontos do episódio",
    },
    {
        "id": "R02",
        "type": "resumo",
        "query": "Quais temas de tecnologia o NerdCast já discutiu?",
        "expected_topics": ["tecnologia", "inovação"],
        "expected_episodes": ["multiple"],
        "notes": "Deve agregar temas de múltiplos episódios",
    },

    # --- CAUSAL ---
    {
        "id": "CA01",
        "type": "causal",
        "query": "Por que a missão Artemis II foi considerada histórica?",
        "expected_topics": ["distância", "lua", "humanidade", "recorde"],
        "expected_episodes": ["NerdCast 1026"],
        "notes": "Deve explicar o impacto histórico baseado nos trechos",
    },
    {
        "id": "CA02",
        "type": "causal",
        "query": "Por que é difícil voltar à Lua depois da Apollo?",
        "expected_topics": ["custo", "tecnologia", "política", "nasa"],
        "expected_episodes": ["NerdCast 1026"],
        "notes": "Deve identificar as razões discutidas no podcast",
    },

    # --- NEGATIVA ---
    {
        "id": "N01",
        "type": "negativa",
        "query": "O que o NerdCast falou sobre criptomoedas e blockchain?",
        "expected_topics": [],
        "expected_episodes": [],
        "notes": "Deve admitir que não tem informação suficiente — não inventar",
    },
    {
        "id": "N02",
        "type": "negativa",
        "query": "Qual foi a opinião do NerdCast sobre o último jogo da Copa do Mundo?",
        "expected_topics": [],
        "expected_episodes": [],
        "notes": "Deve admitir ausência de informação nos trechos disponíveis",
    },
]