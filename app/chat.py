"""
chat.py — Lógica do chatbot com LangChain + Groq

LangChain é um framework que facilita a criação de chatbots com IA.
Ele cuida do histórico de conversa e do formato das mensagens enviadas ao LLM.
O Groq é o provedor de IA: roda o modelo LLaMA 3.1 com latência de ~200ms.
"""

import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain_core.prompts import PromptTemplate

load_dotenv()


# ── CATÁLOGO DE VEÍCULOS ──────────────────────────────────────────────────────
# Texto injetado no system prompt para que a IA conheça os produtos da Revemar.
# O modelo nunca inventa preços — responde apenas com o que está aqui.
CATALOGO = """
AUTOMÓVEIS:
- Toyota Corolla Cross 2024: SUV Compacto, híbrido flex 2.0, a partir de R$ 189.990
  Cores: branco, prata, preto, azul | Garantia: 3 anos | Consumo: 15 km/l

- Volkswagen T-Cross 2024: SUV urbano, 1.4 TSI 150cv, a partir de R$ 149.990
  Cores: branco, vermelho, cinza, laranja | Garantia: 3 anos | Consumo: 12 km/l

- Fiat Strada 2024: picape compacta, 1.3 FireFly 109cv, a partir de R$ 104.990
  Versões: Endurance, Freedom, Volcano | Garantia: 2 anos

MOTOCICLETAS:
- Honda CG 160 Start 2024: a partir de R$ 12.990 | Consumo: 40 km/l
  Ideal para uso urbano e entregas

- Yamaha Factor 150 2024: a partir de R$ 14.490 | Consumo: 38 km/l
  Ótimo custo-benefício para trabalho diário

IMPLEMENTOS AGRÍCOLAS:
- John Deere S680: colheitadeira de alta performance para grandes lavouras
- New Holland TM7040: trator 4x4, 105cv, versátil para diversas culturas
"""


# ── REGRAS DE NEGÓCIO ─────────────────────────────────────────────────────────
# Informações sobre consórcio, seguro e pós-venda também injetadas no prompt.
# A IA responde perguntas sobre esses serviços sem precisar consultar banco de dados.
REGRAS = """
CONSÓRCIO:
- Cartas de crédito de R$ 30.000 a R$ 300.000
- Prazo: 60 a 120 meses | Taxa de administração: 18% total (sem juros)
- Possibilidade de lance para contemplação antecipada

SEGURO:
- Parceria com as principais seguradoras do mercado
- Cobertura: colisão, roubo/furto, terceiros, assistência 24h
- Cotação gratuita mediante cadastro

REVISÃO E PÓS-VENDA:
- Revisões a cada 10.000 km ou 12 meses
- Agendamento: segunda a sábado, 8h às 18h
- Garantia de fábrica honrada em todas as unidades Revemar
"""


# ── SYSTEM PROMPT ─────────────────────────────────────────────────────────────
# O system prompt define a personalidade e as regras do Revemarzinho.
# É enviado ao Groq como a primeira mensagem (antes do histórico do cliente),
# garantindo que a IA siga as diretrizes da Revemar em toda conversa.
SYSTEM_PROMPT = f"""Você é o Revemarzinho, assistente virtual oficial das empresas Revemar.
A Revemar é um grupo com mais de 40 anos de história, presente em 10 estados brasileiros,
atuando em venda de automóveis, motocicletas, implementos agrícolas, consórcio, seguro de veículos e locação.

CATÁLOGO ATUAL:
{CATALOGO}

SERVIÇOS DISPONÍVEIS:
{REGRAS}

REGRAS DE COMPORTAMENTO:
1. Responda SEMPRE em português brasileiro de forma clara, amigável e humana, utilizando emojis para um atendimento mais humanizado.
2. Use APENAS os dados do catálogo acima — nunca invente preços ou especificações.
3. Se não souber a resposta, diga: "Deixa eu verificar com nossa equipe" e sugira que um consultor entre em contato.
4. Quando o cliente demonstrar interesse real em comprar, colete nome completo, telefone com DDD e melhor horário para contato.
5. Para agendamento de test drive ou revisão, colete nome, telefone, modelo de interesse e data/horário preferido.
6. Nunca fale mal de concorrentes.
7. Seja objetivo: respostas entre 3 e 8 linhas, salvo quando o cliente pedir detalhes.
8. Finalize sempre oferecendo ajuda adicional ou próximo passo.
9. IMPORTANTE: Seja BREVE. Máximo 4 linhas por resposta. Respostas longas apenas se explicitamente solicitado.
10. Na PRIMEIRA mensagem do cliente (histórico vazio), SEMPRE se apresente assim:
    "Olá! 👋 Sou o Revemarzinho, assistente virtual da Revemar! 🚗
    Posso te ajudar com orçamentos, vendas, test drive ou revisões.
    Como posso te ajudar hoje? Para encerrar o atendimento, digite *sair* ou *encerrar*."
11. Quando o cliente demonstrar que sua dúvida foi resolvida ou se despedir,
    SEMPRE oriente: "Fico feliz em ter ajudado! 😊 Quando quiser, é só digitar *encerrar* para finalizar o atendimento."
"""


# ── TEMPLATE DE PROMPT ────────────────────────────────────────────────────────
# O PromptTemplate monta o texto final enviado ao Groq a cada mensagem.
# O LangChain preenche {history} com o histórico e {input} com a mensagem atual.
# Assim o modelo sempre "vê" toda a conversa antes de responder.
PROMPT_TEMPLATE = PromptTemplate(
    input_variables=["history", "input"],
    template=f"""{SYSTEM_PROMPT}

Histórico da conversa:
{{history}}

Cliente: {{input}}
Revemarzinho:"""
)


def criar_chain() -> ConversationChain:
    """
    Cria uma chain de conversa com memória vazia para um novo cliente.
    ConversationChain é o componente do LangChain que combina LLM + memória + prompt.
    Esta função é chamada uma vez por sessão, quando o cliente envia a primeira mensagem.
    """
    # ChatGroq inicializa a conexão com a API do Groq
    # temperature=0.7 equilibra criatividade e precisão nas respostas
    llm = ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        temperature=0.7,
        max_tokens=300,
    )

    # ConversationBufferMemory armazena todas as mensagens da sessão em memória RAM
    # return_messages=False retorna o histórico como texto (não como lista de objetos)
    memory = ConversationBufferMemory(
        memory_key="history",
        return_messages=False,
    )

    # ConversationChain conecta tudo: recebe a mensagem, monta o prompt
    # com histórico, envia ao Groq e salva a resposta na memória
    chain = ConversationChain(
        llm=llm,
        memory=memory,
        prompt=PROMPT_TEMPLATE,
        verbose=False,
    )
    return chain


def chat(chain: ConversationChain, mensagem: str) -> str:
    """
    Envia uma mensagem para a chain e retorna a resposta do Revemarzinho.
    O histórico é atualizado automaticamente pelo LangChain após cada chamada.
    O .strip() remove espaços e quebras de linha extras da resposta do LLM.
    """
    resposta = chain.predict(input=mensagem)
    return resposta.strip()
