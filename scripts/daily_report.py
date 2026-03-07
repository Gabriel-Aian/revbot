"""
daily_report.py — Relatório diário de leads
Lê os dados do Google Sheets, calcula KPIs com pandas
e exporta relatório em CSV e HTML.
"""


import os
import sys

# Adiciona a raiz do projeto ao path para importar app.sheets
sys.path.append(os.path.dirname((os.path.dirname(os.path.abspath(__file__)))))

from app.sheets import listarLeads
import pandas as pd
from datetime import datetime

def gerar_relatorio():
    """
    Lê todos os leads da planilha, calcula KPIs e exporta
    os arquivos report.csv e report.html na pasta scripts/output/
    """

    print("Gerando relatório diário de leads...")


    # CARREGAR DADOS
    leads = listarLeads()

    if not leads:
        print("Nenhum lead encontrado na planilha")
        return

    df = pd.DataFrame(leads)
    print(f"{len(df)} leads carregados")

    # DEBUG
    print("Exemplo de timestamp na planilha:", df["timestamp"].iloc[0])
    print("Tipo:", type(df["timestamp"].iloc[0]))


    #LIMPEZA E TIPAGEM
    # Converte timestamp para datetime para filtros por data
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="%d/%m/%Y %H:%M:%S", errors="coerce")
    df["score"] = df["score"].str.lower().str.strip()
    df["interesse"] = df["interesse"].str.lower().str.strip()

    #KPIs GERAIS
    total_leads = len(df)
    leads_quentes = len(df[df["score"] == "quente"])
    leads_mornos = len(df[df["score"] == "morno"])
    leads_frios = len(df[df["score"] == "frio"])
    taxa_quentes = round((leads_quentes / total_leads) *100, 1) if total_leads > 0 else 0

    #Leads de hoje
    hoje = datetime.now().date()
    df_hoje = df[df["timestamp"].dt.date == hoje]
    leads_hoje = len(df_hoje)

    #Distribuição por interesse
    por_interesse = df["interesse"].value_counts().to_dict()

    #Distribuição por score
    por_score = df["score"].value_counts().to_dict()


    #EXIBIÇÃO PELO TERMINAL
    print("\n" + "=" *50)
    print("     RELATÓRIO DE LEADS - REVEMAR")
    print("="*50)
    print(f"Data da geração     : {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"Total de leads      : {total_leads}")
    print(f"Leads de hoje       : {leads_hoje}")
    print(f"Leads quentes       : {leads_quentes}({taxa_quentes}%)")
    print(f"Leads mornos        : {leads_mornos}")
    print(f"Leads frios         : {leads_frios}")
    print("\n Por interesse:")
    for interesse, qtd in por_interesse.items():
        print(f"    {interesse:<20} {qtd}")
    print("\n  Por score:")
    for score, qtd in por_score.items():
        print(f"    {score:<20} {qtd}")
    print("=" * 50 + "\n")


    #EXPORTAR CSV
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)

    csv_path = os.path.join(output_dir, "report.csv")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"CSV exportado: {csv_path}")

    #EXPORTAR HTML
    html_path = os.path.join(output_dir, "report.html")

    html = f"""<!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Relatório de Leads — Revemar</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; color: #333; }}
            h1   {{ color: #0D2B5E; }}
            h2   {{ color: #1A4FA0; margin-top: 30px; }}
            .kpi-grid {{
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 16px;
                margin: 20px 0;
            }}
            .kpi-card {{
                background: #EBF2FD;
                border-left: 5px solid #1A4FA0;
                padding: 16px;
                border-radius: 4px;
            }}
            .kpi-card .valor {{
                font-size: 2em;
                font-weight: bold;
                color: #0D2B5E;
            }}
            .kpi-card .label {{
                font-size: 0.85em;
                color: #4A4A6A;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
                font-size: 0.9em;
            }}
            th {{
                background: #0D2B5E;
                color: white;
                padding: 10px;
                text-align: left;
            }}
            td {{
                padding: 8px 10px;
                border-bottom: 1px solid #DDE3ED;
            }}
            tr:nth-child(even) {{ background: #F3F5F9; }}
            .quente {{ color: #C0392B; font-weight: bold; }}
            .morno  {{ color: #BF5B00; font-weight: bold; }}
            .frio   {{ color: #1A4FA0; font-weight: bold; }}
            footer  {{ margin-top: 40px; color: #999; font-size: 0.8em; }}
        </style>
    </head>
    <body>
        <h1>📊 Relatório de Leads — Revemar</h1>
        <p>Gerado em: <strong>{datetime.now().strftime('%d/%m/%Y às %H:%M')}</strong></p>

        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="valor">{total_leads}</div>
                <div class="label">Total de Leads</div>
            </div>
            <div class="kpi-card">
                <div class="valor">{leads_hoje}</div>
                <div class="label">Leads Hoje</div>
            </div>
            <div class="kpi-card">
                <div class="valor" style="color:#C0392B">{leads_quentes}</div>
                <div class="label">Leads Quentes 🔴</div>
            </div>
            <div class="kpi-card">
                <div class="valor">{taxa_quentes}%</div>
                <div class="label">Taxa de Leads Quentes</div>
            </div>
        </div>

        <h2>Distribuição por Interesse</h2>
        <table>
            <tr><th>Interesse</th><th>Quantidade</th></tr>
            {"".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in por_interesse.items())}
        </table>

        <h2>Todos os Leads</h2>
        <table>
            <tr>
                <th>Data</th><th>Nome</th><th>Telefone</th>
                <th>Interesse</th><th>Score</th><th>Resumo</th>
            </tr>
            {"".join(f'''<tr>
                <td>{row.get("timestamp", "")}</td>
                <td>{row.get("nome", "")}</td>
                <td>{row.get("telefone", "")}</td>
                <td>{row.get("interesse", "")}</td>
                <td class="{row.get("score", "")}">{row.get("score", "").upper()}</td>
                <td>{row.get("resumo", "")}</td>
            </tr>''' for _, row in df.iterrows())}
        </table>

        <footer>RevBot — Sistema de IA Revemar | Relatório gerado automaticamente</footer>
    </body>
    </html>"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Html exportado: {html_path}")
    print("\nRelatório gerado com sucesso")

if __name__ == "__main__":
    gerar_relatorio()