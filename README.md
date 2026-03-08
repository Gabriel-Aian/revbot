# 🚗 RevBot — Assistente IA de Atendimento Revemar

> Chatbot inteligente para atendimento 24h, qualificação automática de leads e
> agendamentos via WhatsApp para o Grupo Revemar.

## 🎯 Problema que Resolve
Leads que chegam fora do horário comercial se perdem. O Revemarzinho
atende automaticamente pelo WhatsApp, qualifica o interesse do cliente com IA
e notifica o consultor certo — sem custo por mensagem adicional.

## 🛠️ Stack Tecnológico

| Camada     | Tecnologia                     | Função                              |
|------------|--------------------------------|-------------------------------------|
| Backend    | Python 3.12 + FastAPI          | API REST com 8 endpoints            |
| IA         | LangChain + Groq (LLaMA 3.1)   | LLM cloud, latência ~200ms          |
| WhatsApp   | UltraMsg                       | Gateway de mensagens WhatsApp       |
| Automação  | N8N Cloud                      | Workflows: roteamento e notificação |
| Frontend   | Streamlit                      | Interface web de demonstração       |
| Dados      | Google Sheets API              | Armazenamento de leads              |
| Cloud      | AWS Lambda + API Gateway       | Deploy serverless em produção       |
| Testes     | Selenium 4 + Edge WebDriver    | Testes E2E automatizados            |

## 🚀 Como Rodar Localmente

### Pré-requisitos
- Python 3.12+
- Conta Groq com API Key: https://console.groq.com
- Credenciais Google Sheets (`credentials.json` na raiz)

### Instalação
```bash
git clone https://github.com/Gabriel-Aian/revbot.git
cd revbot
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
cp .env.example .env        # preencher GROQ_API_KEY e GOOGLE_SHEETS_ID
```

### Execução
```bash
# Terminal 1 — API FastAPI:
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Interface Streamlit:
streamlit run frontend/streamlit_app.py
```
Acesse: http://localhost:8501 | Documentação API: http://localhost:8000/docs

### Deploy na AWS
```powershell
# Empacota, faz upload para S3 e atualiza o Lambda automaticamente:
powershell -ExecutionPolicy Bypass -File deploy.ps1
```
API em produção: https://bpex7uylkh.execute-api.us-east-1.amazonaws.com

## 📁 Estrutura do Projeto
```
revbot/
├── app/
│   ├── main.py          # FastAPI — 8 endpoints + máquina de estados WhatsApp
│   ├── chat.py          # LangChain + Groq — chatbot com memória por sessão
│   ├── lead_scorer.py   # Qualificação automática: quente / morno / frio
│   ├── sheets.py        # Google Sheets API — salva e lista leads
│   └── notifier.py      # Webhooks N8N — dispara notificações
├── frontend/
│   └── streamlit_app.py # Interface web do chatbot
├── scripts/
│   ├── daily_report.py  # Relatório pandas — KPIs em CSV e HTML
│   └── selenium_test.py # Testes E2E — fluxo completo via Edge WebDriver
├── n8n/
│   ├── workflow_leads.json        # Workflow N8N exportado
│   └── workflow_agendamento.json  # Workflow N8N exportado
├── lambda_function.py   # Entry point para AWS Lambda (via Mangum)
├── deploy.ps1           # Script PowerShell de deploy automatizado
├── .env.example         # Modelo de variáveis de ambiente
└── requirements.txt
```

## 🤖 Fluxo WhatsApp (N8N Cloud)
```
Cliente (WhatsApp)
    → UltraMsg (gateway)
    → N8N Cloud (webhook POST /whatsapp)
        → IF: filtra grupos / mensagens próprias
        → FastAPI /chat/whatsapp (AWS Lambda)
            → LangChain + Groq (gera resposta)
            → Máquina de estados (atendimento / agendamento / confirmação)
        → Switch por campo "acao":
            continuar   → responde ao cliente (UltraMsg)
            encerrar    → mensagem de despedida
            consultor   → encaminha para vendedor + salva lead
            agendamento → registra na planilha + notifica consultor
```

## 📈 Progresso do Desenvolvimento

- [x] **Dia 1** — Chatbot IA + Backend FastAPI + Interface Streamlit ✅
- [x] **Dia 2** — Qualificação de leads com IA + Google Sheets ✅
- [x] **Dia 3** — Workflows N8N: notificação de lead quente + confirmação de agendamento ✅
- [x] **Dia 4** — Relatório pandas + Testes E2E Selenium ✅
- [x] **Dia 5** — Deploy AWS Lambda + API Gateway + deploy.ps1 ✅
- [x] **Dia 6** — Integração WhatsApp via UltraMsg + N8N Cloud ✅
- [x] **Dia 7** — Máquina de estados, agendamento automático, correções finais ✅
