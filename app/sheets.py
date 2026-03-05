"""
sheets.py: Integração com Google Sheets
Salva leads e agendamentos na planilha da Revemar.
"""

import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

#Escopos de permissão que serão utilizados
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

#Caminho do arquivo de credenciais na raiz do projeto (credentials.json)
CREDENTIALS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "credentials.json"
)

def _conectar():
    """
    cria e retorna a conexão autenticada com o google sheets, chamada internamente pelas funções publicas
    """
    creds =Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    cliente = gspread.authorize(creds)
    planilha_id = os.getenv("GOOGLE_SHEETS_ID")
    return cliente.open_by_key(planilha_id)


def salvarLead(dados_lead: dict, session_id: str) -> bool:
    """
    Adiciona uma linha nova na aba 'Leads' da planilha.
    Retorna True se salvou com sucesso, False se falhou.

    Colunas esperadas na planilha (na ordem):
    timestamp | nome | telefone | interesse | orcamento | score | resumo | session_id
    """
    try:
        planilha = _conectar()

        #Acessa ou cria a aba 'leads'
        try:
            aba = planilha.worksheet("Leads")
        except gspread.WorksheetNotFound:
            aba = planilha.add_worksheet(title="Leads", rows=1000, cols=10)

            #Cria o cabeçalho se a aba for nova
            aba.append_row([
                "timestamp", "nome", "telefone", "interesse","orcamento", "score", "resumo", "session_id"
            ])

        linha = [
            datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            dados_lead.get("nome") or "Não informado",
            dados_lead.get("telefone") or "Não informado",
            dados_lead.get("interesse") or "outro",
            dados_lead.get("orçamento") or "Não informado",
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
    Retorna todos os leads salvos como lista de dicionários.
    Usado pelo relatório diário (será implementado em: Dia 4).
    """
    try:
        planilha = _conectar()
        aba = planilha.worksheet("Leads")
        return aba.get_all_records()
    except Exception as e:
        print(f"[sheets] Erro ao listar leads: {e}")
        return []