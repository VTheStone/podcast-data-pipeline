"""
Golden dataset for RAG pipeline evaluation.
Covers different query types to validate system quality.

Ground truth fields:
- expected_episode_ids: real `episodes.id` values (RSS guid, from the
  `episodes` table) — NOT titles. Empty list = spans multiple episodes
  or not yet confirmed.
- expected_chunk_ids: ChromaDB ids in the format "{episode_id}_{chunk_index}"
  (see src/processing/indexer.py:110), confirmed relevant by manual review.
  Empty list = not labeled yet.
- reference_answer: human-written gold answer, used later for
  faithfulness/relevance scoring against the generated answer.

Two query shapes require different evaluation strategies:
- Extractive (F02, F03, C01, CA01, CA02): the answer exists verbatim in a
  small, identifiable set of chunks. These get real expected_chunk_ids and
  are scored with retrieval metrics (precision@k, recall@k, MRR).
- Aggregative (F01, R01, R02, C02): the answer is synthesized from many
  scattered mentions with no fixed "correct" chunk set. These are marked
  "N/A" (not "TODO") on the retrieval fields and are scored only at the
  generation level (faithfulness/relevance against reference_answer),
  never against expected_chunk_ids.

When adding new queries to this dataset, label expected_chunk_ids by
running `python -m src.processing.searcher "<query>"` and confirming
which returned chunk ids are actually relevant before filling them in.
"""

EVALUATION_QUERIES = [
    # --- FACTUAL ---
    {
        "id": "F01",
        "type": "factual",
        "query": "Quem é o Alexandre Ottoni?",
        "expected_topics": ["apresentador", "jovem nerd", "host"],
        "expected_episode_ids": [],  # N/A - aggregative query, scored only via generation (M4)
        "expected_chunk_ids": [],  # N/A - aggregative query, scored only via generation (M4)
        "reference_answer": "Alexandre Ottoni é um dos apresentadores e cofundador do NerdCast (Jovem Nerd), ao lado de Azaghal (Deive Pazos).",
        "notes": (
            "Deve identificar o host principal do podcast. Corpus não contém "
            "segmento biográfico sobre o host — auto-introdução é sempre o "
            "jingle padrão (confirmado via src/transcription/intro_patterns/"
            "pt_br.py). Pergunta agregativa: não há conjunto fixo de chunks "
            "corretos."
        ),
    },
    {
        "id": "F02",
        "type": "factual",
        "query": "Quais astronautas participaram da missão Artemis II?",
        "expected_topics": ["Victor Glover", "Reed Wiseman", "Cristina", "Jeremy"],
        "expected_episode_ids": ["0a7470a6-3a8d-11f1-9c02-e3c72f761653"],  # NerdCast 1026
        "expected_chunk_ids": [
            "0a7470a6-3a8d-11f1-9c02-e3c72f761653_35",
            "0a7470a6-3a8d-11f1-9c02-e3c72f761653_39",
            "0a7470a6-3a8d-11f1-9c02-e3c72f761653_42",
            "0a7470a6-3a8d-11f1-9c02-e3c72f761653_44",
            "0a7470a6-3a8d-11f1-9c02-e3c72f761653_46",
            "0a7470a6-3a8d-11f1-9c02-e3c72f761653_47",
            "0a7470a6-3a8d-11f1-9c02-e3c72f761653_48",
        ],
        "reference_answer": "Os quatro astronautas da Artemis II são Reed Wiseman (comandante), Victor Glover, Christina Koch e Jeremy Hansen — este último em seu primeiro voo espacial, enquanto os outros três já tinham experiência anterior no espaço.",
        "notes": "Deve listar os 4 astronautas corretamente",
    },
    {
        "id": "F03",
        "type": "factual",
        "query": "O que é o programa Artemis da NASA?",
        "expected_topics": ["lua", "nasa", "missão tripulada", "exploração"],
        "expected_episode_ids": ["0a7470a6-3a8d-11f1-9c02-e3c72f761653"],  # NerdCast 1026
        "expected_chunk_ids": ["0a7470a6-3a8d-11f1-9c02-e3c72f761653_33"],
        "reference_answer": "O programa Artemis é a iniciativa da NASA para levar a humanidade de volta à Lua, composta por várias missões (como a Artemis I, não tripulada, e a Artemis II, tripulada) além de missões de carga, com o objetivo de estabelecer presença lunar sustentável.",
        "notes": "Deve explicar o programa sem inventar datas ou detalhes",
    },

    # --- COMPARATIVA ---
    {
        "id": "C01",
        "type": "comparativa",
        "query": "Qual a diferença entre a Artemis I e a Artemis II?",
        "expected_topics": ["tripulada", "não tripulada", "teste"],
        "expected_episode_ids": ["0a7470a6-3a8d-11f1-9c02-e3c72f761653"],  # NerdCast 1026
        "expected_chunk_ids": [
            "0a7470a6-3a8d-11f1-9c02-e3c72f761653_22",
            "0a7470a6-3a8d-11f1-9c02-e3c72f761653_33",
        ],
        "reference_answer": "A Artemis I (2022) foi uma missão de teste não tripulada, usada para validar sistemas como o escudo de reentrada da cápsula Orion. A Artemis II também foi uma missão de teste, mas tripulada, levando quatro astronautas para orbitar a Lua e voltar, sem pousar.",
        "notes": "Deve distinguir corretamente as duas missões",
    },
    {
        "id": "C02",
        "type": "comparativa",
        "query": "Como o NerdCast compara exploração espacial com outros temas de ciência?",
        "expected_topics": ["ciência", "tecnologia", "espaço"],
        "expected_episode_ids": [],  # N/A - aggregative query, scored only via generation (M4)
        "expected_chunk_ids": [],  # N/A - aggregative query, scored only via generation (M4)
        "reference_answer": "O NerdCast trata exploração espacial como um entre vários temas recorrentes de ciência, ao lado de séries como 'A Ciência dos Super-Heróis' e 'Mitos da Ciência' — cobrindo espaço em episódios como 'Colonizando o Espaço' e 'O Espaço Disputado', sem tratá-lo como o tema central único do podcast.",
        "notes": (
            "Teste de cross-episode — deve buscar em múltiplos episódios. "
            "Pergunta agregativa: não há conjunto fixo de chunks/episódios "
            "corretos."
        ),
    },

    # --- RESUMO ---
    {
        "id": "R01",
        "type": "resumo",
        "query": "Sobre o que foi o episódio do NerdCast sobre Artemis II?",
        "expected_topics": ["lua", "astronautas", "nasa", "missão"],
        "expected_episode_ids": ["0a7470a6-3a8d-11f1-9c02-e3c72f761653"],  # NerdCast 1026 — known target episode
        "expected_chunk_ids": [],  # N/A - aggregative/summary query, scored only via generation (M4)
        "reference_answer": "O episódio cobre a missão Artemis II da NASA: o voo tripulado mais distante já feito por seres humanos, a tripulação (incluindo Victor Glover, Reed Wiseman e Christina Koch), a diferença em relação à Artemis I (não tripulada), os desafios técnicos e de custo do foguete SLS e da cápsula Orion, e o contexto político e orçamentário da NASA.",
        "notes": (
            "Deve sintetizar os principais pontos do episódio. Pergunta "
            "agregativa dentro do episódio: não há um chunk único que "
            "resuma o conteúdo."
        ),
    },
    {
        "id": "R02",
        "type": "resumo",
        "query": "Quais temas de tecnologia o NerdCast já discutiu?",
        "expected_topics": ["tecnologia", "inovação"],
        "expected_episode_ids": [],  # N/A - aggregative query, scored only via generation (M4)
        "expected_chunk_ids": [],  # N/A - aggregative query, scored only via generation (M4)
        "reference_answer": "O NerdCast já discutiu temas de tecnologia como inteligência artificial (incluindo episódios sobre ChatGPT e IA), a história e cultura da internet, privacidade digital, a série 'Tecnologias do Futuro' (com pelo menos 4 episódios), jogos de tabuleiro/videogames e cientistas em empresas de tecnologia.",
        "notes": (
            "Deve agregar temas de múltiplos episódios. Pergunta agregativa: "
            "não há conjunto fixo de chunks/episódios corretos."
        ),
    },

    # --- CAUSAL ---
    {
        "id": "CA01",
        "type": "causal",
        "query": "Por que a missão Artemis II foi considerada histórica?",
        "expected_topics": ["distância", "lua", "humanidade", "recorde"],
        "expected_episode_ids": ["0a7470a6-3a8d-11f1-9c02-e3c72f761653"],  # NerdCast 1026
        "expected_chunk_ids": [
            "0a7470a6-3a8d-11f1-9c02-e3c72f761653_7",
            "0a7470a6-3a8d-11f1-9c02-e3c72f761653_11",
            "0a7470a6-3a8d-11f1-9c02-e3c72f761653_19",
            "0a7470a6-3a8d-11f1-9c02-e3c72f761653_27",
        ],
        "reference_answer": "A Artemis II foi considerada histórica por levar seres humanos à maior distância da Terra já alcançada, repetindo o feito do programa Apollo décadas depois, com apenas cerca de 22 pessoas na história tendo vivenciado essa perspectiva.",
        "notes": "Deve explicar o impacto histórico baseado nos trechos",
    },
    {
        "id": "CA02",
        "type": "causal",
        "query": "Por que é difícil voltar à Lua depois da Apollo?",
        "expected_topics": ["custo", "tecnologia", "política", "nasa"],
        "expected_episode_ids": ["0a7470a6-3a8d-11f1-9c02-e3c72f761653"],  # NerdCast 1026
        "expected_chunk_ids": [
            "0a7470a6-3a8d-11f1-9c02-e3c72f761653_8",
            "0a7470a6-3a8d-11f1-9c02-e3c72f761653_54",
            "0a7470a6-3a8d-11f1-9c02-e3c72f761653_63",
            "0a7470a6-3a8d-11f1-9c02-e3c72f761653_65",
        ],
        "reference_answer": "Voltar à Lua é difícil por causa do custo altíssimo de cada lançamento (na faixa de bilhões de dólares), da complexidade tecnológica exigida, e de cortes e instabilidade no orçamento da NASA ao longo de diferentes governos, o que atrasa repetidamente os cronogramas.",
        "notes": "Deve identificar as razões discutidas no podcast",
    },

    # --- NEGATIVA ---
    {
        "id": "N01",
        "type": "negativa",
        "query": "O que o NerdCast falou sobre criptomoedas e blockchain?",
        "expected_topics": [],
        "expected_episode_ids": [],
        "expected_chunk_ids": [],
        "reference_answer": "Não há informação suficiente nos episódios indexados.",
        "notes": "Deve admitir que não tem informação suficiente — não inventar",
    },
    {
        "id": "N02",
        "type": "negativa",
        "query": "Qual foi a opinião do NerdCast sobre o último jogo da Copa do Mundo?",
        "expected_topics": [],
        "expected_episode_ids": [],
        "expected_chunk_ids": [],
        "reference_answer": "Não há informação suficiente nos episódios indexados.",
        "notes": "Deve admitir ausência de informação nos trechos disponíveis",
    },
]