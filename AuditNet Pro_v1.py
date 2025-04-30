import os
import sys
import subprocess
import logging
import paramiko
import difflib
import smtplib
from email.message import EmailMessage
import requests
from dotenv import load_dotenv
from datetime import datetime
import schedule
import time
import json

# Configuração de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Função para verificar e instalar módulos necessários
def install_required_modules():
    """
    Verifica e instala automaticamente os módulos necessários.
    """
    required_modules = ['python-dotenv', 'paramiko', 'schedule', 'requests']
    for module in required_modules:
        try:
            __import__(module.replace("-", "_"))
            logging.info(f"Módulo '{module}' já está instalado.")
        except ImportError:
            logging.warning(f"Módulo '{module}' não encontrado. Instalando...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', module])
            logging.info(f"Módulo '{module}' instalado com sucesso.")

# Instalar módulos antes de continuar
install_required_modules()

# Função para solicitar informações do usuário
def request_user_input():
    """
    Solicita as credenciais e informações necessárias do usuário.
    """
    # Solicitar informações de email
    email_sender = input("Por favor, insira o endereço de email do remetente: ")
    email_password = input("Por favor, insira a senha do email do remetente: ")
    email_recipients = input("Por favor, insira os endereços de email dos destinatários (separados por vírgula): ")

    # Solicitar webhook do Slack
    slack_webhook = input("Por favor, insira o Webhook do Slack: ")

    # Solicitar informações dos dispositivos
    devices = []
    while True:
        name = input("Insira o nome do dispositivo (ou pressione Enter para finalizar): ")
        if not name:
            break
        ip = input(f"Insira o IP do dispositivo '{name}': ")
        username = input(f"Insira o nome de usuário para acessar '{name}': ")
        password = input(f"Insira a senha para acessar '{name}': ")
        command = input(f"Insira o comando para coletar configuração de '{name}': ")
        devices.append({"name": name, "ip": ip, "username": username, "password": password, "command": command})

    # Salvar as entradas como variáveis de ambiente temporárias
    os.environ["EMAIL_SENDER"] = email_sender
    os.environ["EMAIL_PASSWORD"] = email_password
    os.environ["EMAIL_RECIPIENTS"] = email_recipients
    os.environ["SLACK_WEBHOOK"] = slack_webhook
    os.environ["DEVICES"] = json.dumps(devices)
    logging.info("Informações necessárias coletadas com sucesso.")

# Solicitar informações antes de carregar variáveis
request_user_input()

# Carregar variáveis de ambiente
def load_environment():
    """
    Carrega variáveis de ambiente do arquivo .env (se existir) ou das variáveis coletadas.
    """
    email_sender = os.getenv("EMAIL_SENDER")
    email_password = os.getenv("EMAIL_PASSWORD")
    email_recipients = os.getenv("EMAIL_RECIPIENTS").split(",")
    slack_webhook = os.getenv("SLACK_WEBHOOK")
    devices = json.loads(os.getenv("DEVICES", "[]"))
    if not all([email_sender, email_password, email_recipients, slack_webhook, devices]):
        logging.error("Credenciais ou informações dos dispositivos estão incompletas.")
        sys.exit(1)
    logging.info("Variáveis de ambiente carregadas com sucesso.")
    return email_sender, email_password, email_recipients, slack_webhook, devices

# Garante que os diretórios necessários existem
def ensure_directories():
    """
    Garante que os diretórios necessários para backups e relatórios existam.
    """
    directories = ["backups", "reports"]
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logging.info(f"Diretório '{directory}' criado com sucesso.")

# Classe para gerenciar dispositivos e coleta de configuração
class DeviceManager:
    def __init__(self, device):
        self.name = device.get("name")
        self.ip = device.get("ip")
        self.username = device.get("username")
        self.password = device.get("password")
        self.command = device.get("command")

        if not all([self.name, self.ip, self.username, self.password, self.command]):
            logging.error(f"Dispositivo mal configurado: {device}")
            raise ValueError("Todos os campos do dispositivo são obrigatórios.")

    def collect_config(self):
        """
        Conecta ao dispositivo via SSH e coleta configuração.
        """
        try:
            logging.info(f"Conectando ao dispositivo {self.name} ({self.ip}) via SSH...")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.ip, username=self.username, password=self.password)
            stdin, stdout, stderr = ssh.exec_command(self.command)
            output = stdout.read().decode().strip()
            ssh.close()
            logging.info(f"Configuração coletada com sucesso de {self.name}.")
            return output
        except Exception as e:
            logging.error(f"Erro ao coletar configuração de {self.name} ({self.ip}): {e}")
            return None

# Função principal para executar auditorias
def audit_configs(devices):
    """
    Executa auditorias nos dispositivos fornecidos.
    """
    logging.info("Iniciando auditoria de configurações...")
    for device_data in devices:
        try:
            device = DeviceManager(device_data)
            config = device.collect_config()
            if config:
                logging.info(f"Configuração coletada: {config[:100]}...")  # Exemplo de log truncado
        except Exception as e:
            logging.error(f"Erro durante a auditoria do dispositivo {device_data.get('name')}: {e}")
    logging.info("Auditoria de configurações concluída.")

# Configuração do programa principal
if __name__ == "__main__":
    email_sender, email_password, email_recipients, slack_webhook, devices = load_environment()
    ensure_directories()
    schedule.every().week.do(audit_configs, devices)
    while True:
        schedule.run_pending()
        time.sleep(1)
