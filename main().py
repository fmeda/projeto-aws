import sys
import subprocess
import boto3
import os
from ratelimit import limits
from time import sleep
import logging
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

# Configuração de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Função para instalar pacotes necessários
def install_required_packages():
    required_packages = ['boto3', 'ratelimit']
    for package in required_packages:
        try:
            __import__(package)
            logging.info(f"Pacote '{package}' já instalado.")
        except ImportError:
            logging.warning(f"Pacote '{package}' não encontrado. Instalando...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install_required_packages()

# Função para criar chave no AWS KMS
def routine_create_kms_key(report_path):
    try:
        session = boto3.Session(profile_name='default')
        client = session.client('kms', region_name='us-east-1')
        response = client.create_key(
            Description='Chave para criptografia de dados do SecureScanOps',
            KeyUsage='ENCRYPT_DECRYPT',
            Origin='AWS_KMS'
        )
        key_id = response['KeyMetadata']['KeyId']
        logging.info(f"Chave criada com sucesso: {key_id}")

        with open(report_path, 'a') as report_file:
            report_file.write(f"Chave criada com sucesso: {key_id}\n")
        
        return key_id
    except NoCredentialsError:
        logging.error("Erro: Credenciais não encontradas.")
        return None
    except PartialCredentialsError:
        logging.error("Erro: Credenciais incompletas.")
        return None
    except Exception as e:
        logging.error(f"Erro inesperado: {e}")
        return None

# Função para criptografar dados
def routine_encrypt_data(data, key_id, report_path):
    try:
        session = boto3.Session(profile_name='default')
        client = session.client('kms', region_name='us-east-1')
        response = client.encrypt(
            KeyId=key_id,
            Plaintext=data.encode('utf-8')
        )
        encrypted_data = response['CiphertextBlob']
        logging.info("Dados criptografados com sucesso.")

        with open(report_path, 'a') as report_file:
            report_file.write("Dados do usuário criptografados com sucesso.\n")
        
        return encrypted_data
    except Exception as e:
        logging.error(f"Erro ao criptografar dados: {e}")
        return None

# Função principal para coleta de dados e execução
def main():
    """
    Função principal para coleta de dados do usuário e execução das rotinas.
    """
    # Diretório para gerar o relatório
    report_path = os.path.join(os.getcwd(), "kms_report.txt")
    
    # Solicitar os dados específicos do usuário
    user_name = input("Por favor, insira seu Nome: ")
    user_email = input("Por favor, insira seu Email: ")
    user_phone = input("Por favor, insira seu Telefone: ")

    # Combinar os dados em um único formato
    user_data = f"Nome: {user_name}, Email: {user_email}, Telefone: {user_phone}"
    
    # Criar chave no AWS KMS
    key_id = routine_create_kms_key(report_path)
    
    if key_id:
        # Criptografar os dados fornecidos pelo usuário
        encrypted_data = routine_encrypt_data(user_data, key_id, report_path)
        
        if encrypted_data:
            logging.info(f"Dados criptografados foram salvos no relatório: {report_path}")
        else:
            logging.error("Erro ao criptografar os dados do usuário.")
    else:
        logging.error("Chave KMS não criada. Processo abortado.")

# Executar a função principal
if __name__ == "__main__":
    main()
