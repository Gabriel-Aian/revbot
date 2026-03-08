"""
lead_scorer.py — Qualificação automática de leads com IA

Quando o cliente encerra o atendimento, esta módulo envia o histórico
completo da conversa para o Groq com um prompt específico de extração.
O modelo retorna um JSON estruturado com dados do cliente e o score (quente/morno/frio).
"""

import json
import os
import re

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate

load_dotenv()


# ── PROMPT DE EXTRAÇÃO ────────────────────────────────────────────────────────
# Este prompt instrui o Groq a agir como analista, não como assistente.
# A chave é pedir APENAS JSON — sem texto antes ou depois — para que
# o resultado possa ser parseado diretamente com json.loads().
SCORER_PROMPT = PromptTemplate(
    input_variables=["historico"],
    template="""
Você é um analista de leads de uma concessionária. Analise a conversa abaixo e extraia as informações do cliente em formato JSON.

CONVERSA:
{historico}

Retorne APENAS um objeto JSON válido, sem texto adicional, sem markdown, sem explicações. Siga EXATAMENTE esta estrutura:

{{
    "nome": "nome do cliente ou null se não informado",
    "telefone": "telefone com DDD ou null se não informado",
    "interesse": "um de: automovel | motocicleta | implemento | consorcio | seguro | revisao | outro",
    "modelo_interesse": "modelo específico mencionado ou null",
    "orcamento": "faixa de orçamento mencionada ou null",
    "score": "quente | morno | frio",
    "resumo": "resumo da conversa em uma linha",
    "agendar": true ou false
}}

CRITÉRIOS DE SCORE:
- quente: cliente perguntou preço, pediu test drive, mencionou orçamento ou quer falar com vendedor
- morno: cliente demonstrou interesse mas ainda está pesquisando
- frio: apenas curiosidade geral, sem intenção clara de compra

IMPORTANTE: Retorne SOMENTE o JSON. Nenhuma palavra antes ou depois.
"""
)


def extrair_historico_txt(chain) -> str:
    """
    Extrai o histórico de mensagens da memória LangChain como texto simples.
    O LangChain armazena mensagens como objetos (HumanMessage/AIMessage),
    então precisamos convertê-los para string antes de enviar ao scorer.
    """
    memoria = chain.memory
    mensagens = memoria.chat_memory.messages

    if not mensagens:
        return ""

    linhas = []
    for msg in mensagens:
        # HumanMessage = cliente, AIMessage = Revemarzinho
        tipo = "Cliente" if msg.__class__.__name__ == "HumanMessage" else "Revemarzinho"
        linhas.append(f"{tipo}: {msg.content}")

    return "\n".join(linhas)


def analisar_lead(chain) -> dict:
    """
    Analisa o histórico da conversa e retorna os dados estruturados do lead.
    Cria uma instância separada do Groq com temperature=0.1 para respostas
    mais determinísticas — o scorer precisa de precisão, não de criatividade.
    """
    historico = extrair_historico_txt(chain)

    if not historico:
        return _lead_vazio()

    # temperature=0.1 torna a IA mais precisa e menos criativa
    # max_tokens=500 é suficiente para o JSON de resposta
    llm = ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        temperature=0.1,
        max_tokens=500,
    )

    prompt_formatado = SCORER_PROMPT.format(historico=historico)

    try:
        resposta = llm.invoke(prompt_formatado)
        texto = resposta.content.strip()

        # Mesmo pedindo só JSON, LLMs às vezes adicionam texto ao redor
        texto_limpo = _extrair_json(texto)
        dados = json.loads(texto_limpo)

        return _normalizar(dados)

    except (json.JSONDecodeError, Exception) as e:
        print(f"[lead_scorer] Erro ao analisar: {e}")
        return _lead_vazio()


def _extrair_json(texto: str) -> str:
    """
    Extrai o bloco JSON de um texto que pode ter conteúdo antes ou depois.
    Usa regex para encontrar o primeiro par de chaves { } no texto.
    É um "seguro" para quando o LLM desobedece a instrução de retornar só JSON.
    """
    match = re.search(r'\{.*\}', texto, re.DOTALL)
    if match:
        return match.group()
    return texto


def _normalizar(dados: dict) -> dict:
    """
    Garante que todos os campos esperados existam no dicionário retornado.
    Se o LLM omitir algum campo, preenchemos com None/False para não gerar KeyError.
    Chamado após o json.loads() para garantir a estrutura completa.
    """
    campos = ["nome", "telefone", "interesse", "modelo_interesse", "orcamento", "score", "resumo", "agendar"]
    for campo in campos:
        if campo not in dados:
            dados[campo] = None if campo != "agendar" else False
    return dados


def _lead_vazio() -> dict:
    """
    Retorna um lead padrão quando a análise falha ou o histórico está vazio.
    Evita que erros na IA quebrem o fluxo de salvamento na planilha.
    Score "frio" é o valor mais conservador para não gerar falsos alertas ao consultor.
    """
    return {
        "nome": None,
        "telefone": None,
        "interesse": "outro",
        "modelo_interesse": None,
        "orcamento": None,
        "score": "frio",
        "resumo": "Conversa sem dados suficientes para análise",
        "agendar": False,
    }


# Mantém compatibilidade com código existente que usa camelCase
analisarLead = analisar_lead
extrairHistoricoTxt = extrair_historico_txt
