# 🚗 Revemarzinho — Assistente IA de Atendimento Revemar

> Chatbot inteligente para atendimento 24h, qualificação de leads e
> agendamentos automáticos para concessionárias e distribuidoras do
> grupo Revemar.

## 🎯 Problema que Resolve
Leads que chegam fora do horário comercial se perdem. O Revemarzinho
atende, qualifica e notifica o vendedor certo — sem custo adicional.

## 🛠️ Stack Tecnológico

| Camada     | Tecnologia                  | Função                        |
|------------|-----------------------------|-------------------------------|
| Backend    | Python + FastAPI            | API REST do chatbot           |
| IA         | LangChain + Ollama (LLaMA 3)| LLM local, custo zero         |
| Automação  | N8N                         | Workflows de lead e agendamento|
| Frontend   | Streamlit                   | Interface web de demonstração |
| Dados      | Google Sheets API           | Armazenamento de leads        |
| Cloud      | AWS Lambda + API Gateway    | Deploy em produção            |

## 🚀 Como Rodar Localmente

### Pré-requisitos
- Python 3.12+
- [Ollama](https://ollama.com) instalado com modelo `llama3`

### Instalação
```bash
git clone https://github.com/seuusuario/revbot.git
cd revbot
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### Execução
```bash
# Terminal 1 — API:
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Interface:
streamlit run frontend/streamlit_app.py
```
Acesse: http://localhost:8501

## 📁 Estrutura do Projeto
```
revbot/
├── app/
│   ├── main.py          # FastAPI — rotas da API
│   ├── chat.py          # LangChain + Ollama — lógica do chatbot
│   ├── lead_scorer.py   # Qualificação de leads com IA (Dia 2)
│   ├── sheets.py        # Google Sheets API (Dia 2)
│   └── notifier.py      # Webhook N8N (Dia 3)
├── frontend/
│   └── streamlit_app.py # Interface web do chatbot
├── scripts/             # Relatórios e testes (Dia 4)
├── n8n/                 # Workflows N8N exportados (Dia 3)
├── .env.example         # Modelo de variáveis de ambiente
└── requirements.txt
```

## 📈 Progresso do Desenvolvimento

- [x] **Dia 1** — Chatbot IA + Backend FastAPI + Interface Streamlit ✅
- [ ] **Dia 2** — Qualificação de leads + Google Sheets
- [ ] **Dia 3** — Workflows N8N (agendamento + notificações)
- [ ] **Dia 4** — Relatório Python + Testes Selenium
- [ ] **Dia 5** — Deploy AWS + Documentação final
```

Depois commite o README:
```
git add README.md
git commit -m "docs: README atualizado — Dia 1 concluído"
git push origin main
