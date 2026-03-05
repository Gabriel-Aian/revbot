"""
streamlit_app.py — Interface web do RevBot
Roda em http://localhost:8501 e se comunica com a FastAPI em: 8000
"""

import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Assistente Revemar - Revemarzinho",
    page_icon=":robot_face:",
    layout="centered",
)

# ESTADO DA SESSÃO
# st.session_state persiste entre interações do usuário na mesma aba
if "historico" not in st.session_state:
    st.session_state.historico = []
if "sessionId" not in st.session_state:
    st.session_state.sessionId = None


# FUNÇÕES

def enviarMensagem(mensagem: str) -> str:
    """Chama o endpoint /chat da FastAPI e retorna a resposta da mensagem"""
    payload = {
        "mensagem": mensagem,
        "sessionId": st.session_state.sessionId,
    }
    try:
        r = requests.post(f"{API_URL}/chat", json=payload, timeout=120)
        data = r.json()
        st.session_state.sessionId = data["sessionId"]
        return data["resposta"]
    except requests.exceptions.ConnectionError:
        return "API offline. execute no terminal: uvicorn  app.main:app -- reload"
    except Exception as e:
        return f"Erro: {str(e)}"


def resetarConversa():
    """Limpa o histórico local e apaga a sessão na API."""
    if st.session_state.sessionId:
        try:
            requests.delete(f"{API_URL}/chat/{st.session_state.sessionId}")
        except:
            pass
    st.session_state.historico = []
    st.session_state.sessionId = None

#INTERFACE
st.title("Assistente Revemar - Revemarzinho")
st.caption("Assistente virtual das empresas Revemar - Atendimento Inteligente 24horas")
st.divider()

# Histórico do chat
chatArea = st.container(height=450)
with chatArea:
    if not st.session_state.historico:
        st.info("Olá! Sou o Revemarzinho, assistente virtual da Revemar. Como posso ajudar você hoje?")

    for msg in st.session_state.historico:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# Input + botão reset
colInput, colReset = st.columns([5, 1])
with colInput:
    userInput = st.chat_input("Digite sua mensagem...")
with colReset:
    if st.button("Resetar", use_container_width=True):
        resetarConversa()
        st.rerun()

#Processa imagem
if userInput:
    st.session_state.historico.append({"role": "user", "content": userInput})

    with st.spinner("Revemarzinho está analisando..."):
        resposta = enviarMensagem(userInput)

    st.session_state.historico.append({"role": "assistant", "content": resposta})
    st.rerun()

# Painel de debug
with st.expander("Sessão"):
    st.text(f"Session ID : {st.session_state.sessionId or 'Nova Sessão'}")
    st.text(f"Mensagens : {len(st.session_state.historico)}")