"""
lead_scorer.py — Qualificação automática de leads com IA
Analisa o histórico da conversa e extrai dados estruturados do cliente.
"""
from langchain_classic.chains.qa_with_sources.stuff_prompt import template
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
import json
import os
import re

load_dotenv()

# PROMPT DE ANÁLISE
# Instruímos IA a agir como analista e não como assistente
# Saída deve ser apenas json -  sem texto antes ou depois

SCORER_PROMPT = PromptTemplate(
    input_variables=["historico"],
    template="""
    Você é um analista de leads  de uma concessionária. Analise a conversa abaixo e extraia as informações do cliente em formato JSON.
    CONVERSA:
    {historico}
    
    Retorne APENAS um objeto JSON válido, sem texto adicional, sem markdown, sem explicações. Siga EXATAMENTE esta estrutura:
    
    {{
        "nome": "nome do cliente ou null se não informado",
        "telefone": "telefone com DDD ou null se não informado",
        "interesse": "um de: automovel | motocicleta | implemento | consorcio | seguro | revisao | outro",
        "modelo_interesse": "modelo específico mencionada ou null",
        "orcamento": "faixa de orçamento mencionada ou null",
        "score": "quente | morno | frio",
        "resumo": "resumo da conversa em uma linha",
        "agendar": true ou false
    }}
    CRITÉRIOS DE SCORE:
    - quente: cliente perguntou preço, pedio test drive, mencionou orçamento ou quer falar com vendedor
    - morno: cliente demonstrou interesse mas ainda está pesquisando
    - frio: apenas curiosidade geral, sem intenção clara de compra
    
    IMPORTANTE: Retorne SOMENTE o JSON. Nenhuma palavra antes ou depois.
    """
)


def extrairHistoricoTxt(chain) -> str:
    """
     extrai historico da conversationbuffermemory como texto simples, Langchain armazena internamente. Precisa ser convertido para string
    """
    memoria = chain.memory
    mensagens = memoria.chat_memory.messages

    if not mensagens:
        return ""

    linhas = []
    for msg in mensagens:
        # HumanMessage = CLiente, AIMessage =  Revemarzinho
        tipo = "CLiente" if msg.__class__.__name__ == "HumanMessage" else "Revemarzinho"
        linhas.append(f"{tipo}: {msg.content}")

    return "\n".join(linhas)


def analisarLead(chain) -> dict:
    """
    Analisa o historico da conversa e retorna os dados do lead, retorna um dicionario com os campos extraídos pela Ia
    """
    historico = extrairHistoricoTxt(chain)

    if not historico:
        return _lead_vazio()

    llm = ChatOllama(
        model = os.getenv("OLLAMA_MODEL", "llama3"),
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature = 0.1,
        num_predict = 300
    )

    prompt_formatado = SCORER_PROMPT.format(historico=historico)

    try:
        resposta = llm.invoke(prompt_formatado)
        texto = resposta.content.strip()

        #tenta extrair JSON mesmo se o modelo adicionou texto ao redor
        textoLimpo = _extrair_json(texto)
        dados = json.loads(textoLimpo)

        #garante que todos os campos existem
        return _normalizar(dados)

    except (json.JSONDecodeError, Exception) as e:
        print(f"[lead_scorer] Erro ao analisar: {e}")
        print(f"[lead_scorer] Resposta recebida: {textoLimpo if 'texto' in dir() else 'sem resposta'}")
        return _lead_vazio()

def _extrair_json(texto: str) -> str:
    """
    tenta encontrar um bloco JSON no texto mesmo se o modelo adicionou palavras antes ou depois(obs: Comum em llms)
    """
    #tenta encontrar conteudo entre chaves
    match = re.search(r'\{.*\}', texto, re.DOTALL)
    if match:
        return match.group()
    return texto


def _normalizar(dados: dict) -> dict:
    """
    garante que todos os campos esperados existem no dicionario
    """
    campos = ["nome", "telefone", "interesse", "modelo_interesse", "orcamento", "score", "resumo", "agendar"]
    for campo in campos:
        if campo not in dados:
            dados[campo] = None if campo != "agendar" else False
    return dados


def _lead_vazio() -> dict:
    """Retorna um lead padrão quando a análise falha."""
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