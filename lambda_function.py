"""
lambda_function.py — Entry point do AWS Lambda

O Lambda não sabe executar um servidor FastAPI diretamente.
Ele chama uma função handler(event, context) com os dados da requisição.
O Mangum (importado via app.main) faz a tradução: evento Lambda → FastAPI → resposta HTTP.
"""

from app.main import handler  # noqa: F401 — handler é o entry point configurado no Lambda
