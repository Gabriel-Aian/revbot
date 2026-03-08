"""
sheets.py — Integração com Google Sheets via gspread

gspread é uma biblioteca Python que permite ler e escrever em planilhas Google.
A autenticação usa uma Service Account (credentials.json) — uma conta de serviço
criada no Google Cloud que tem permissão de editar a planilha específica da Revemar.
"""

import os
from datetime import datetime, timezone, timedelta

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

load_dotenv()


# ── ESCOPOS DE PERMISSÃO ──────────────────────────────────────────────────────
# Escopos definem o que a Service Account pode fazer no Google.
# spreadsheets: leitura e escrita em planilhas.
# drive: necessário para abrir planilhas pelo ID (não só pelo nome).
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Caminho absoluto para credentials.json na raiz do projeto
# os.path.dirname(__file__) = pasta app/ | dirname novamente = raiz do projeto
CREDENTIALS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "credentials.json"
)


def _conectar():
    """
    Cria e retorna a conexão autenticada com o Google Sheets.
    Lê o credentials.json, gera o token OAuth e abre a planilha pelo ID do .env.
    É uma função privada (prefixo _) — só usada internamente por salvarLead e listarLeads.
    """
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    cliente = gspread.authorize(creds)
    planilha_id = os.getenv("GOOGLE_SHEETS_ID")
    return cliente.open_by_key(planilha_id)


def salvarLead(dados_lead: dict, session_id: str) -> bool:
    """
    Adiciona uma linha nova na aba 'Leads' da planilha com os dados do cliente.
    Cria a aba e o cabeçalho automaticamente se ainda não existirem.
    Retorna True se salvou com sucesso, False se ocorreu qualquer erro.

    Ordem das colunas na planilha:
    timestamp | nome | telefone | interesse | orcamento | score | resumo | session_id
    """
    try:
        planilha = _conectar()

        # worksheet() lança WorksheetNotFound se a aba não existir — criamos ela
        try:
            aba = planilha.worksheet("Leads")
        except gspread.WorksheetNotFound:
            aba = planilha.add_worksheet(title="Leads", rows=1000, cols=10)
            aba.append_row([
                "timestamp", "nome", "telefone", "interesse",
                "orcamento", "score", "resumo", "session_id",
            ])

        # Fuso horário -3h = Brasília (UTC-3)
        linha = [
            datetime.now(timezone(timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M:%S"),
            dados_lead.get("nome") or "Não informado",
            dados_lead.get("telefone") or "Não informado",
            dados_lead.get("interesse") or "outro",
            dados_lead.get("orcamento") or "Não informado",
            dados_lead.get("score") or "frio",
            dados_lead.get("resumo") or "",
            session_id,
        ]

        aba.append_row(linha)
        print(f"[sheets] Lead salvo: {dados_lead.get('nome')} | score: {dados_lead.get('score')}")
        return True

    except Exception as e:
        print(f"[sheets] Erro ao salvar lead: {e}")
        return False


def listarLeads() -> list:
    """
    Retorna todos os leads salvos como lista de dicionários Python.
    get_all_records() usa a primeira linha como cabeçalho e transforma cada
    linha seguinte em um dicionário {coluna: valor} — pronto para o pandas.
    """
    try:
        planilha = _conectar()
        aba = planilha.worksheet("Leads")
        return aba.get_all_records()
    except Exception as e:
        print(f"[sheets] Erro ao listar leads: {e}")
        return []
