"""
main.py — API FastAPI do RevBot
Expõe endpoints HTTP consumidos pelo Streamlit e futuramente pelo N8N.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from contextlib import asynccontextmanager
from app.lead_scorer import analisarLead
from app.sheets import salvarLead
import uuid

from app.chat import criar_chain, chat

@asynccontextmanager
async def lifespan(app):
    print("Iniciando...")
    sessoes["__warmup__"] =  criar_chain()
    #envia uma mensagem curta para forçar o carregamento na memória
    chat(sessoes["__warmup__"], "Olá!")
    del sessoes["__warmup__"]
    print("Modelo carregado e pronto!")
    yield

app = FastAPI(
    title="RevBot API",
    description="Assistente IA de atendimento Revemar",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS permite que o streamlit (porta 8501) acesse esta API (porta 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dicionário em memória: Cada cliente tem sua própria chain com histórico independente
sessoes: dict = {}

#MODELOS DE DADOS
#Pydantic valida e documenta automaticamente os dados da API

class chatRequest(BaseModel):
    mensagem: str
    sessionId: Optional[str] = None

class ChatResponse(BaseModel):
    resposta: str
    sessionId: str

class LeadResponse(BaseModel):
    score: str
    nome: Optional[str]
    telefone: Optional[str]
    interesse: Optional[str]
    resumo: str
    salvo_planilha: bool

#ENDPOINTS

@app.get("/")
def raiz():
    """Verificação de saúde da API"""
    return {"status": "online", "serviço": "RevBot API", "versão": "1.0.0"}
@app.post("/chat", response_model=ChatResponse)
def endpoint_chat(request: chatRequest):
    """
       Endpoint principal. Recebe mensagem, mantém sessão e retorna resposta do LLM.
       Se session_id não for enviado, uma nova sessão é criada automaticamente.
    """
    sessionId = request.sessionId or str(uuid.uuid4())

    if sessionId not in sessoes:
        sessoes[sessionId] = criar_chain()

    chain = sessoes[sessionId]

    try:
        resposta = chat(chain, request.mensagem)
        return ChatResponse(resposta=resposta, sessionId=sessionId)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/leads/{sessionId}", response_model=LeadResponse)
def endpoint_lead(sessionId: str):
    """
    Analisa a conversa de uma sessão e salva o lead no Google Sheets.
    Chamado pelo Streamlit quando o usuário clica em 'Encerrar Atendimento'.
    """
    if sessionId not in sessoes:
        raise HTTPException(status_code=404, detail= "Sessão não encontrada")

    chain = sessoes[sessionId]
    dados = analisarLead(chain)
    salvo = salvarLead(dados, sessionId)

    return LeadResponse(
        score=dados["score"],
        nome=dados["nome"],
        telefone=dados["telefone"],
        interesse=dados["interesse"],
        resumo=dados["resumo"],
        salvo_planilha=salvo
    )

@app.delete("/chat/{sessionId}")
def resetarSessao(sessionId: str):
    """Apaga o histórico de uma sessão (usadop pelo botão Reset do Streamlit)."""
    if sessionId in sessoes:
        del sessoes[sessionId]
    return {"mensagem": "Sessão resetada", "sessionId": sessionId}

@app.get("/sessoes")
def listarSessoes():
    """Debug: mostra quantas sessões estão ativas."""
    return  {"sessoes_ativas": len(sessoes), "ids": list(sessoes.keys())}