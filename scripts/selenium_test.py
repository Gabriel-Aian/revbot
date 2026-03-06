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
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


STREAMLIT_URL = "http://localhost:8501"


# Mensagens simulando um lead quente
CONVERSA_TESTE = [
    "Olá, tenho interesse em comprar um carro",
    "Gostaria de saber mais sobre o T-Cross, meu orçamento é até R$ 160 mil",
    "Meu nome é Carlos Teste e meu telefone é 94991234567",
    "Quero agendar um test drive para essa semana",
]


def configurar_driver() ->webdriver.Chrome:
    """
    Configura o Chrome em modo headless — roda sem abrir janela visual.
    Troque headless=True para False se quiser ver o browser durante o teste.
    """
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")
    return webdriver.chrome(options=options)


def aguardar_resposta(driver, wait, mensagens_antes: int, timeout: int = 90):
    """
    Aguarda o assistente responder verificando se o número
    de mensagens no histórico aumentou.
    """
    print(f"Aguardando resposta (timeout {timeout}s)...")
    inicio = time.time()
    while time.time() - inicio < timeout:
        mensagens = driver.find_elements(By.CSS_SELECTOR, "[data-testid='stChatMessage']")
        if len(mensagens) > mensagens_antes:
            return True
        time.sleep(2)
    return False


def executar_teste():
    """Executa o fluxo completo de teste E2E."""
    print("\n Iniciando teste E2E do RevBot...")
    print(f" URL: {STREAMLIT_URL}\n")

    driver = configurar_driver()
    wait = WebDriverWait(driver, 30)
    erros = []


    try:
        # 1 - abrir o streamlit
        print("1 - abrindo o streamlit...")
        driver.get(STREAMLIT_URL)
        time.sleep(3)

        # verifica se a página carregou
        assert "Revemarzinho" in driver.title or "Revemar" in driver.page_source , \ "página do streamlit não carregou corretamente"
        print("Streamlit carregado\n")

        # 2 - enviar mensagens da conversa
        print("2 - simulando conversa...")
        for i, mensagem in enumerate(CONVERSA_TESTE):
            print(f"Mensagem {i+1}: {mensagem[:50]}...")

            #localiza campo de input do chat
            input_field = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "[data-testid='stChatInputTextArea']")
                )
            )

            mensagens_antes = len(
                driver.find_elements(By.CSS_SELECTOR, "[data-testid='stChatMessage']")
            )

            # Digita e envia a mensagem
            input_field.click()
            input_field.send_keys(mensagem)
            input_field.send_keys(Keys.RETURN)

            # Aguarda resposta do assistente
            respondeu = aguardar_resposta(driver, wait, mensagens_antes + 1)
            if respondeu:
                print(f"Resposta recebida\n")
            else:
                erros.append(f"Timeout na mensagem{i+1}")
                print(f"Timeout -  sem resposta\n")
        # 3 - encerrar atendimento
        print("3 - Encerrando atendimento e qualificando lead...")
        botao_encerrar = wait.until(
            EC.element_to_be_clickable((By.XPATH,"//button[@title='Encerrar e salvar lead']" ))
        )
        botao_encerrar.click()
        time.sleep(60) #aguarda análise do LLM

        #verifica se o card do lead apareceu
        page_source = driver.page_source
        if "Lead Qualificado" in page_source:
            print(f"Lead exibido \n")
        else:
            erros.append("Card do lead não apareceu corretamente")
            print("card não encontrado\n")

        # 4 - Capturar screenshot
        print("4 - Capturando screenshot...")
        screenshots_dir = os.path.join(os.path.dirname(__file__), "output")
        os.makedirs(screenshots_dir, exist_ok=True)

        screenshot_path = os.path.join(
            screenshots_dir,
            f"teste_e2e_{time.strftime('%Y%m%d_%H%M%S')}.png"
        )
        driver.save_screenshot(screenshot_path)
        print(f"   ✅ Screenshot salvo: {screenshot_path}\n")

    except Exception as e:
        erros.append(f"Erro inesperado: {str(e)}")
        print(f"   ❌ Erro: {str(e)}\n")
    finally:
        driver.quit()

        #resultado final
        print("=" * 50)
        if not erros:
            print("TODOS OS TESTES PASSARAM")
        else:
            print(f"{len(erros)} ERRO(S) ENCONTRADO(S):")
            for erro in erros:
                print(f"   • {erro}")
        print("=" * 50 + "\n")

        return len(erros) == 0

if __name__ == "__main__":
    sucesso = executar_teste()
    sys.exit(0 if sucesso else 1)