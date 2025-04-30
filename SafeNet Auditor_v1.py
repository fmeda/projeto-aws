import sys
import subprocess
import os
import logging
import base64
from cryptography.fernet import Fernet
from datetime import datetime
import smtplib
from email.message import EmailMessage
import json

# Configuração do logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Função para verificar e instalar módulos necessários
def install_required_modules():
    """
    Verifica e instala automaticamente os módulos necessários.
    """
    required_modules = ['cryptography', 'gspread', 'oauth2client']
    for module in required_modules:
        try:
            __import__(module)
            logging.info(f"Módulo '{module}' já está instalado.")
        except ImportError:
            logging.warning(f"Módulo '{module}' não encontrado. Instalando...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', module])
            logging.info(f"Módulo '{module}' instalado com sucesso.")

# Instalar os módulos antes de continuar
install_required_modules()

# Função para adicionar diretório ao PATH do sistema
def add_to_path(directory):
    """
    Adiciona um diretório ao PATH do sistema, se ainda não estiver presente.
    """
    try:
        current_path = os.environ.get("PATH", "")
        
        # Verifica se o diretório já está no PATH
        if directory in current_path:
            logging.info(f"O diretório '{directory}' já está presente no PATH.")
        else:
            # Adiciona o diretório ao PATH
            os.environ["PATH"] = current_path + os.pathsep + directory
            logging.info(f"Diretório '{directory}' adicionado ao PATH com sucesso.")
            
            # Atualiza o PATH permanentemente (apenas no Windows)
            if os.name == "nt":
                subprocess.run(
                    f'setx PATH "{os.environ["PATH"]}"',
                    shell=True,
                    check=True,
                )
                logging.info("PATH atualizado permanentemente no sistema.")
    except Exception as e:
        logging.error(f"Erro ao adicionar diretório ao PATH: {e}")

# Adicionar diretório de scripts Python ao PATH
python_scripts_dir = os.path.join(
    os.environ.get("LOCALAPPDATA"),
    "Programs",
    "Python",
    "Python313",
    "Scripts"
)
if os.path.exists(python_scripts_dir):
    add_to_path(python_scripts_dir)
else:
    logging.warning(f"O diretório '{python_scripts_dir}' não existe. Verifique sua instalação do Python.")

# Gerar chave para encriptação
def generate_encryption_key():
    key = Fernet.generate_key()
    with open("encryption.key", "wb") as key_file:
        key_file.write(key)
    logging.info("Chave de encriptação gerada e salva no arquivo 'encryption.key'.")
    return key

# Carregar chave para encriptação
def load_encryption_key():
    try:
        with open("encryption.key", "rb") as key_file:
            return key_file.read()
    except FileNotFoundError:
        logging.error("Arquivo de chave de encriptação não encontrado. Gerando nova chave...")
        return generate_encryption_key()

# Encriptar dados
def encrypt_data(data, key):
    fernet = Fernet(key)
    encrypted = fernet.encrypt(data.encode("utf-8"))
    return encrypted

# Desencriptar dados (caso necessário)
def decrypt_data(encrypted_data, key):
    fernet = Fernet(key)
    decrypted = fernet.decrypt(encrypted_data).decode("utf-8")
    return decrypted

# Função para solicitar credenciais ao usuário
def get_credentials():
    logging.info("Solicitando credenciais ao usuário...")
    aws_access_key = input("Por favor, insira sua AWS Access Key: ")
    aws_secret_key = input("Por favor, insira sua AWS Secret Key: ")
    email = input("Por favor, insira seu email para envio de relatórios (opcional): ")
    return {
        "aws_access_key": aws_access_key,
        "aws_secret_key": aws_secret_key,
        "email": email
    }

# Função para salvar as credenciais de forma encriptada
def save_encrypted_credentials(credentials, key):
    encrypted_credentials = {
        k: encrypt_data(v, key).decode("utf-8") if v else "" for k, v in credentials.items()
    }
    with open("credentials.json", "w") as cred_file:
        json.dump(encrypted_credentials, cred_file)
    logging.info("Credenciais encriptadas e salvas em 'credentials.json'.")

# Função para gerar relatório estruturado
def generate_report(equipment_id, findings):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_name = f"scan_report_{equipment_id}_{timestamp}.txt"
    report_path = os.path.join(os.getcwd(), report_name)
    with open(report_path, "w") as report_file:
        report_file.write("RELATÓRIO DE VARRREDURA\n")
        report_file.write(f"ID do Equipamento: {equipment_id}\n")
        report_file.write(f"Data e Hora: {datetime.now()}\n")
        report_file.write("\nVulnerabilidades Encontradas:\n")
        for finding in findings:
            report_file.write(f"- {finding['ip']}: {finding['vulnerability']} (Gravidade: {finding['severity']})\n")
    logging.info(f"Relatório gerado em: {report_path}")
    return report_path

# Função para enviar o relatório por email
def send_email_report(email, report_path):
    if not email:
        logging.info("Email não fornecido. Relatório não será enviado.")
        return

    try:
        msg = EmailMessage()
        msg["Subject"] = "Relatório de Varredura de Vulnerabilidades"
        msg["From"] = "noreply@example.com"
        msg["To"] = email

        with open(report_path, "r") as report_file:
            report_content = report_file.read()

        msg.set_content("Segue o relatório de varredura em anexo.")
        msg.add_attachment(report_content, filename=os.path.basename(report_path))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            # Configure suas credenciais de email aqui
            server.login("seu.email@gmail.com", "sua_senha")
            server.send_message(msg)

        logging.info(f"Relatório enviado para {email}.")
    except Exception as e:
        logging.error(f"Erro ao enviar email: {e}")

# Função principal
def main():
    logging.info("Iniciando o programa...")
    
    # Carregar ou gerar chave de encriptação
    encryption_key = load_encryption_key()

    # Solicitar credenciais ao usuário
    credentials = get_credentials()

    # Salvar credenciais encriptadas
    save_encrypted_credentials(credentials, encryption_key)

    # Simular resultados de varredura
    equipment_id = "server_critical_19216801"
    findings = [
        {"ip": "192.168.1.10", "vulnerability": "SSL Vulnerability", "severity": "High"},
        {"ip": "192.168.1.20", "vulnerability": "Outdated Software", "severity": "Medium"}
    ]

    # Gerar relatório estruturado
    report_path = generate_report(equipment_id, findings)

    # Enviar relatório por email
    send_email_report(credentials.get("email"), report_path)

if __name__ == "__main__":
    main()
