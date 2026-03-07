"""
selenium_test.py — Teste E2E automatizado com Selenium
Simula uma conversa completa no Streamlit e valida o fluxo de ponta a ponta.
ATENÇÃO: Execute apenas com FastAPI, Streamlit e Ollama rodando.
"""

import time
import sys
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

STREAMLIT_URL = "http://localhost:8501"

# Caminho do EdgeDriver na raiz do projeto
DRIVER_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "msedgedriver.exe"
)

# Mensagens simulando um lead quente
CONVERSA_TESTE = [
    "Olá, tenho interesse em comprar um carro",
    "Gostaria de saber mais sobre o T-Cross, meu orçamento é até R$ 160 mil",
    "Meu nome é Carlos Teste e meu telefone é 94991234567",
    "Quero agendar um test drive para essa semana",
]


def configurarDriver() -> webdriver.Edge:
    """
    Configura o Edge em modo headless — roda sem abrir janela visual.
    Mude headless para False se quiser ver o browser durante o teste.
    """
    options = EdgeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")

    service = EdgeService(executable_path=DRIVER_PATH)
    return webdriver.Edge(service=service, options=options)


def aguardarResposta(driver, mensagens_antes: int, timeout: int = 90) -> bool:
    """
    Aguarda o assistente responder verificando se o número
    de mensagens no histórico aumentou.
    """
    print(f"     Aguardando resposta (timeout: {timeout}s)...")
    inicio = time.time()
    while time.time() - inicio < timeout:
        mensagens = driver.find_elements(By.CSS_SELECTOR, "[data-testid='stChatMessage']")
        if len(mensagens) > mensagens_antes:
            return True
        time.sleep(2)
    return False


def executarTeste():
    """Executa o fluxo completo de teste E2E."""
    print("\n Iniciando teste E2E do RevBot...")
    print(f"   URL: {STREAMLIT_URL}\n")

    driver = configurarDriver()
    wait   = WebDriverWait(driver, 30)
    erros  = []

    try:
        # PASSO 1: Abrir o Streamlit
        print(" Passo 1: Abrindo o Streamlit...")
        driver.get(STREAMLIT_URL)
        time.sleep(4)

        assert "Revemarzinho" in driver.page_source or "Revemar" in driver.page_source, \
            "Página do Streamlit não carregou corretamente"
        print("    Streamlit carregado\n")

        # PASSO 2: Enviar mensagens
        print(" Passo 2: Simulando conversa...")
        for i, mensagem in enumerate(CONVERSA_TESTE):
            print(f"    Mensagem {i+1}: {mensagem[:50]}...")

            input_field = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "[data-testid='stChatInputTextArea']")
                )
            )

            mensagens_antes = len(
                driver.find_elements(By.CSS_SELECTOR, "[data-testid='stChatMessage']")
            )

            input_field.click()
            input_field.send_keys(mensagem)
            input_field.send_keys(Keys.RETURN)

            respondeu = aguardarResposta(driver, mensagens_antes + 1)
            if respondeu:
                print(f"    Resposta recebida\n")
            else:
                erros.append(f"Timeout na mensagem {i+1}")
                print(f"    Timeout — sem resposta\n")


        # PASSO 3: Encerrar atendimento
        print(" Passo 3: Encerrando atendimento e qualificando lead...")
        time.sleep(2)

        # Tenta localizar o botão "✅" por múltiplas estratégias
        botao_encerrar = None

        # Estratégia 1 — pelo title
        try:
            botao_encerrar = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[@title='Encerrar e salvar lead']")
                )
            )
        except:
            pass

        # Estratégia 2 — pelo texto/emoji do botão
        if not botao_encerrar:
            try:
                botao_encerrar = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[contains(., '✅')]")
                    )
                )
            except:
                pass

        # Estratégia 3 — pelo índice (terceiro botão da página)
        if not botao_encerrar:
            try:
                botoes = driver.find_elements(By.TAG_NAME, "button")
                print(f"    Botões encontrados: {len(botoes)}")
                for i, b in enumerate(botoes):
                    print(f"      Botão {i}: text='{b.text}' title='{b.get_attribute('title')}'")
                # Tenta o terceiro botão (Reset=1, Encerrar=2)
                if len(botoes) >= 3:
                    botao_encerrar = botoes[2]
            except:
                pass

        if botao_encerrar:
            driver.execute_script("arguments[0].click();", botao_encerrar)
            print("    Botão de encerramento clicado\n")
            time.sleep(60)
        else:
            erros.append("Botão de encerramento não encontrado")
            print("    Botão não encontrado\n")

        if "Lead Qualificado" in driver.page_source:
            print("    Card do lead exibido\n")
        else:
            erros.append("Card do lead não apareceu após encerramento")
            print("    Card do lead não encontrado\n")

        # PASSO 4: Capturar screenshot
        print(" Passo 4: Capturando screenshot...")
        screenshots_dir = os.path.join(os.path.dirname(__file__), "output")
        os.makedirs(screenshots_dir, exist_ok=True)

        screenshot_path = os.path.join(
            screenshots_dir,
            f"teste_e2e_{time.strftime('%Y%m%d_%H%M%S')}.png"
        )
        driver.save_screenshot(screenshot_path)
        print(f"    Screenshot salvo: {screenshot_path}\n")

    except Exception as e:
        erros.append(f"Erro inesperado: {str(e)}")
        print(f"    Erro: {str(e)}\n")

    finally:
        driver.quit()

    # ── RESULTADO FINAL ───────────────────────────────────────────────────────
    print("="*50)
    if not erros:
        print(" TODOS OS TESTES PASSARAM")
    else:
        print(f" {len(erros)} ERRO(S) ENCONTRADO(S):")
        for erro in erros:
            print(f"   • {erro}")
    print("="*50 + "\n")

    return len(erros) == 0


if __name__ == "__main__":
    sucesso = executarTeste()
    sys.exit(0 if sucesso else 1)