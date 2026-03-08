"""
main.py — Servidor principal do RevBot (FastAPI)

FastAPI é um framework Python que cria APIs REST de alta performance.
Cada função com @app.get/@app.post se torna uma URL que outras aplicações
(Streamlit, N8N, WhatsApp via UltraMsg) podem chamar via HTTP.
"""

import os
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from pydantic import BaseModel

from app.chat import criar_chain, chat
from app.lead_scorer import analisarLead
from app.notifier import notificarLead, notificarAgendamento
from app.sheets import salvarLead


# ── INICIALIZAÇÃO DO SERVIDOR ─────────────────────────────────────────────────
# lifespan executa código uma única vez quando o servidor inicia.
# O "warmup" envia uma mensagem vazia para o Groq, fazendo o modelo
# carregar na memória — assim a primeira mensagem real do cliente não sofre atraso.
@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("AWS_LAMBDA_FUNCTION_NAME") is None:
        print("Iniciando warmup local...")
        sessoes["__warmup__"] = criar_chain()
        chat(sessoes["__warmup__"], "Olá!")
        sessoes.pop("__warmup__")
    yield


app = FastAPI(
    title="RevBot API",
    description="Assistente IA de atendimento Revemar",
    version="1.0.0",
    lifespan=lifespan,
)


# ── CORS (Cross-Origin Resource Sharing) ─────────────────────────────────────
# Permite que o Streamlit (porta 8501) chame a API (porta 8000) no mesmo computador.
# Sem esse middleware, o navegador bloquearia as requisições por "origens diferentes".
# Em produção real, trocar allow_origins=["*"] pelo domínio específico da aplicação.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── ESTADO EM MEMÓRIA ─────────────────────────────────────────────────────────
# sessoes: dicionário que guarda o histórico LangChain de cada cliente.
# estados: dicionário que guarda em qual etapa do fluxo cada cliente está.
# A chave de ambos é o session_id (número WhatsApp ou UUID do Streamlit).
sessoes: dict = {}
estados: dict = {}  # valores possíveis: "atendimento" | "aguardando_confirmacao" | "agendamento_revisao" | "agendamento_test_drive"

NUMERO_CONSULTOR = "5547999234865@c.us"


# ── PALAVRAS-CHAVE PARA DETECÇÃO DE INTENÇÃO ─────────────────────────────────
# Quando a mensagem do cliente contém uma dessas palavras, o sistema muda
# o estado da conversa sem precisar perguntar à IA — mais rápido e confiável.
# KEYWORDS_DATA são usadas para detectar quando o cliente já informou uma data.
KEYWORDS_REVISAO = [
    "revisão", "revisao", "manutenção", "manutencao",
    "oficina", "reparar", "conserto", "agendar revisão", "agendar revisao",
]
KEYWORDS_TEST_DRIVE = [
    "test drive", "test-drive", "testdrive", "agendar test",
    "quero testar", "experimentar o carro", "dirigir o carro",
]
KEYWORDS_DATA = [
    "segunda", "terça", "terca", "quarta", "quinta", "sexta", "sábado", "sabado",
    "manhã", "manha", "tarde", "dia ", "/20", "janeiro", "fevereiro", "março", "marco",
    "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
    "novembro", "dezembro", "amanhã", "amanha", "semana",
]


# ── MODELOS DE DADOS (PYDANTIC) ───────────────────────────────────────────────
# Pydantic define o "contrato" da API: quais campos são obrigatórios,
# quais são opcionais e qual o tipo de cada um.
# O FastAPI valida automaticamente e retorna HTTP 422 se algo estiver errado.

class ChatRequest(BaseModel):
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


class AgendamentoRequest(BaseModel):
    nome: str
    email_cliente: str
    servico: str
    modelo: str
    data_horario: str


class AgendamentoResponse(BaseModel):
    mensagem: str
    notificado: bool


# Modelo usado pelo endpoint WhatsApp (chamado pelo N8N)
# nome e telefone chegam preenchidos pelo próprio WhatsApp (pushname e "from")
class ChatWhatsAppRequest(BaseModel):
    mensagem: str
    session_id: str
    historico: Optional[list] = []
    nome: Optional[str] = None
    telefone: Optional[str] = None


class ChatWhatsAppResponse(BaseModel):
    resposta: str
    session_id: str
    acao: str   # "continuar" | "encerrar" | "consultor" | "agendamento"
    lead: Optional[dict] = None


# ── FUNÇÃO AUXILIAR ───────────────────────────────────────────────────────────
# A IA tenta extrair nome e telefone da conversa, mas pode errar.
# Esta função sobrescreve esses campos com os dados reais do WhatsApp,
# que são sempre confiáveis: pushname = nome salvo no celular, from = número.
def _enriquecer_lead(dados: dict, request: ChatWhatsAppRequest) -> dict:
    if request.nome:
        dados["nome"] = request.nome
    if request.telefone:
        dados["telefone"] = request.telefone
    return dados


# ════════════════════════════════════════════════════════════════════════════════
# ENDPOINTS DA API
# ════════════════════════════════════════════════════════════════════════════════

# ── GET / ─────────────────────────────────────────────────────────────────────
# Verifica se o servidor está no ar — usado pela AWS e pelo N8N.
# Retorna JSON simples; se responder, a API está funcionando.
@app.get("/")
def raiz():
    return {"status": "online", "serviço": "RevBot API", "versão": "1.0.0"}


# ── POST /chat ────────────────────────────────────────────────────────────────
# Endpoint principal consumido pelo Streamlit (interface web).
# Cria uma nova sessão se o cliente não tiver uma, depois chama o LLM.
# O sessionId é gerado automaticamente e devolvido para o Streamlit guardar.
@app.post("/chat", response_model=ChatResponse)
def endpoint_chat(request: ChatRequest):
    session_id = request.sessionId or str(uuid.uuid4())
    if session_id not in sessoes:
        sessoes[session_id] = criar_chain()
    chain = sessoes[session_id]
    try:
        resposta = chat(chain, request.mensagem)
        return ChatResponse(resposta=resposta, sessionId=session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── POST /leads/{sessionId} ───────────────────────────────────────────────────
# Qualifica o lead de uma sessão: busca o histórico, envia à IA para análise,
# salva o resultado no Google Sheets e dispara webhook no N8N.
# Chamado pelo botão ✅ do Streamlit ao final do atendimento.
@app.post("/leads/{sessionId}", response_model=LeadResponse)
def endpoint_lead(sessionId: str):
    if sessionId not in sessoes:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    chain = sessoes[sessionId]
    dados = analisarLead(chain)
    salvo = salvarLead(dados, sessionId)
    notificarLead(dados, sessionId)
    return LeadResponse(
        score=dados["score"],
        nome=dados["nome"],
        telefone=dados["telefone"],
        interesse=dados["interesse"],
        resumo=dados["resumo"],
        salvo_planilha=salvo,
    )


# ── POST /agendamento ─────────────────────────────────────────────────────────
# Registra agendamento enviado pelo formulário do Streamlit.
# Os dados chegam já preenchidos; o notifier dispara o webhook N8N
# que envia o e-mail de confirmação para o cliente.
@app.post("/agendamento", response_model=AgendamentoResponse)
def endpoint_agendamento(request: AgendamentoRequest):
    dados = {
        "nome": request.nome,
        "email_cliente": request.email_cliente,
        "servico": request.servico,
        "modelo": request.modelo,
        "data_horario": request.data_horario,
    }
    notificado = notificarAgendamento(dados)
    return AgendamentoResponse(
        mensagem="Agendamento registrado com sucesso!" if notificado else "Agendamento registrado, mas notificação falhou!",
        notificado=notificado,
    )


# ── POST /chat/whatsapp ───────────────────────────────────────────────────────
# Endpoint chamado pelo N8N a cada mensagem recebida no WhatsApp.
# Implementa uma máquina de estados: o campo "acao" no retorno diz ao N8N
# o que fazer — continuar respondendo, encerrar, chamar consultor ou registrar agendamento.
#
# Diagrama de estados:
#   atendimento ──(sair)──────────────► aguardando_confirmacao ──(sim)──► encerrar
#               ──(revisão)───────────► agendamento_revisao    ──(não)──► consultor
#               ──(test drive)────────► agendamento_test_drive
#               agendamento_* ──(data)──► agendamento → volta para atendimento
@app.post("/chat/whatsapp", response_model=ChatWhatsAppResponse)
def chat_whatsapp(request: ChatWhatsAppRequest):
    session_id = request.session_id
    mensagem_lower = request.mensagem.strip().lower()

    # Primeira mensagem: cria sessão e define estado inicial
    if session_id not in sessoes:
        sessoes[session_id] = criar_chain()
        estados[session_id] = "atendimento"

    estado_atual = estados.get(session_id, "atendimento")

    # ── ESTADO: aguardando_confirmacao ────────────────────────────────────────
    # O bot perguntou se conseguiu ajudar. Aqui processamos a resposta SIM/NÃO.
    # SIM: encerra e salva o lead. NÃO: redireciona para consultor humano.
    # Outro texto: repete a pergunta até receber uma resposta válida.
    if estado_atual == "aguardando_confirmacao":

        if mensagem_lower in ["sim", "s"]:
            chain = sessoes[session_id]
            dados = _enriquecer_lead(analisarLead(chain), request)
            salvarLead(dados, session_id)
            notificarLead(dados, session_id)
            sessoes.pop(session_id, None)
            estados.pop(session_id, None)
            return ChatWhatsAppResponse(
                resposta="Fico feliz em ter ajudado! Até a próxima. 😊🚗",
                session_id=session_id,
                acao="encerrar",
                lead=dados,
            )

        elif mensagem_lower in ["não", "nao", "n"]:
            chain = sessoes[session_id]
            dados = _enriquecer_lead(analisarLead(chain), request)
            salvarLead(dados, session_id)
            notificarLead(dados, session_id)
            sessoes.pop(session_id, None)
            estados.pop(session_id, None)
            return ChatWhatsAppResponse(
                resposta="Entendido! Vou te conectar com um de nossos consultores. Em breve alguém entrará em contato. 👨‍💼",
                session_id=session_id,
                acao="consultor",
                lead=dados,
            )

        else:
            return ChatWhatsAppResponse(
                resposta="Por favor, digite SIM para encerrar ou NAO para falar com um consultor. 😊",
                session_id=session_id,
                acao="continuar",
            )

    # ── ESTADO: agendamento_revisao / agendamento_test_drive ──────────────────
    # A IA coleta modelo e data/horário através da conversa normal.
    # Quando uma data for detectada pelas keywords, o agendamento é concluído
    # e o estado volta para "atendimento" para continuar o atendimento normal.
    if estado_atual in ["agendamento_revisao", "agendamento_test_drive"]:
        tipo = "Revisão" if estado_atual == "agendamento_revisao" else "Test Drive"

        # Permite sair do fluxo de agendamento a qualquer momento
        if any(cmd in mensagem_lower for cmd in ["sair", "encerrar", "tchau", "até logo"]):
            estados[session_id] = "aguardando_confirmacao"
            return ChatWhatsAppResponse(
                resposta="Consegui ajudar você hoje? 😊\nDigite SIM para encerrar ou NAO para falar com um consultor.",
                session_id=session_id,
                acao="continuar",
            )

        resposta = chat(sessoes[session_id], request.mensagem)

        # Verifica se uma data foi mencionada no histórico inteiro + mensagem atual
        historico_buffer = ""
        try:
            historico_buffer = sessoes[session_id].memory.buffer or ""
        except Exception:
            pass

        texto_completo = historico_buffer + " " + request.mensagem
        tem_data = any(kw in texto_completo.lower() for kw in KEYWORDS_DATA)

        if tem_data:
            chain = sessoes[session_id]
            dados = _enriquecer_lead(analisarLead(chain), request)
            salvarLead(dados, session_id)
            estados[session_id] = "atendimento"
            return ChatWhatsAppResponse(
                resposta=resposta,
                session_id=session_id,
                acao="agendamento",
                lead={**dados, "tipo_agendamento": tipo},
            )

        return ChatWhatsAppResponse(
            resposta=resposta,
            session_id=session_id,
            acao="continuar",
        )

    # ── ESTADO: atendimento normal ────────────────────────────────────────────
    # Estado padrão: o Revemarzinho responde livremente usando o LLM Groq.
    # A cada mensagem, verificamos se o cliente quer sair, agendar algo
    # ou continuar a conversa — e mudamos o estado quando necessário.

    if any(cmd in mensagem_lower for cmd in ["sair", "encerrar", "tchau", "até logo"]):
        estados[session_id] = "aguardando_confirmacao"
        return ChatWhatsAppResponse(
            resposta="Consegui ajudar você hoje? 😊\nDigite SIM para encerrar ou NAO para falar com um consultor.",
            session_id=session_id,
            acao="continuar",
        )

    if any(kw in mensagem_lower for kw in KEYWORDS_REVISAO):
        estados[session_id] = "agendamento_revisao"
    elif any(kw in mensagem_lower for kw in KEYWORDS_TEST_DRIVE):
        estados[session_id] = "agendamento_test_drive"

    # Recarrega histórico externo enviado pelo Streamlit (sincronização)
    if request.historico:
        chain = sessoes[session_id]
        chain.memory.clear()
        for msg in request.historico:
            if msg["role"] == "user":
                chain.memory.chat_memory.add_user_message(msg["content"])
            else:
                chain.memory.chat_memory.add_ai_message(msg["content"])

    resposta = chat(sessoes[session_id], request.mensagem)
    return ChatWhatsAppResponse(
        resposta=resposta,
        session_id=session_id,
        acao="continuar",
    )


# ── POST /chat/encerrar/{session_id} ─────────────────────────────────────────
# Encerramento manual via API (usado pelo Streamlit no botão ✅).
# Qualifica o lead, salva na planilha e libera a memória do servidor.
@app.post("/chat/encerrar/{session_id}")
def encerrar_conversa(session_id: str):
    if session_id not in sessoes:
        return {"mensagem": "Sessão não encontrada", "lead": None}
    chain = sessoes[session_id]
    dados = analisarLead(chain)
    salvo = salvarLead(dados, session_id)
    notificarLead(dados, session_id)
    sessoes.pop(session_id, None)
    estados.pop(session_id, None)
    return {
        "mensagem": "Conversa encerrada e lead qualificado",
        "lead": dados,
        "salvo_planilha": salvo,
    }


# ── DELETE /chat/{sessionId} ──────────────────────────────────────────────────
# Apaga a sessão sem qualificar o lead — botão Reset do Streamlit.
# Usado para reiniciar uma conversa do zero durante testes ou demonstrações.
@app.delete("/chat/{sessionId}")
def resetar_sessao(sessionId: str):
    if sessionId in sessoes:
        del sessoes[sessionId]
    estados.pop(sessionId, None)
    return {"mensagem": "Sessão resetada", "sessionId": sessionId}


# ── GET /sessoes ──────────────────────────────────────────────────────────────
# Retorna quantas sessões estão ativas no momento — útil para monitoramento.
@app.get("/sessoes")
def listar_sessoes():
    return {"sessoes_ativas": len(sessoes), "ids": list(sessoes.keys())}


# ── AWS LAMBDA HANDLER ────────────────────────────────────────────────────────
# Mangum converte o evento do Lambda (dicionário Python) em uma requisição HTTP
# que o FastAPI consegue processar. O Lambda chama handler(event, context)
# e o Mangum faz toda a tradução internamente — sem nenhuma mudança no código FastAPI.
handler = Mangum(app)
