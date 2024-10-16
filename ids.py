import re
import subprocess
import time
import glob
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import logging
import os

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("log_monitoring.log"),
        logging.StreamHandler()
    ]
)

# Diretório contendo os arquivos de log
log_directory = "/www/wwwlogs"
log_pattern = "*access*"

# Expressões regulares para capturar o IP e verificar as requisições
regex_ip = re.compile(r"^(\d+\.\d+\.\d+\.\d+)")  # IP deve estar na primeira coluna
regex_404 = re.compile(r' 404 ')
regex_403 = re.compile(r' 403 ')
regex_401 = re.compile(r' 401 ')
regex_wp_login = re.compile(r' /wp-login.php')

# Conjunto de IPs já suspensos para evitar duplicidade
suspended_ips = set()
suspended_ips_lock = threading.Lock()

# Dicionários para contar tentativas por IP
attempts_errors = defaultdict(int)  # Inclui 401, 403, 404
attempts_wp_login = defaultdict(int)
attempts_lock = threading.Lock()

# Tempo de suspensão em segundos (exemplo: 1 hora)
suspension_time = 3600  # 1 hora
ip_suspension_time = {}
ip_suspension_lock = threading.Lock()

# Função para adicionar IP ao conjunto 'ids_ban' do nftables
def suspend_ip(ip):
    with suspended_ips_lock:
        if ip not in suspended_ips:
            logging.info(f"Suspending IP: {ip}")
            try:
                subprocess.run(
                    ["sudo", "nft", "add", "element", "ip", "filter", "ids_ban", f'{{ {ip} }}'],
                    check=True
                )
                suspended_ips.add(ip)
                with ip_suspension_lock:
                    ip_suspension_time[ip] = time.time()
            except subprocess.CalledProcessError as e:
                logging.error(f"Erro ao suspender IP {ip}: {e}")

# Função para remover IP do conjunto 'ids_ban' do nftables
def unsuspend_ip(ip):
    with suspended_ips_lock:
        if ip in suspended_ips:
            logging.info(f"Unsuspending IP: {ip}")
            try:
                subprocess.run(
                    ["sudo", "nft", "delete", "element", "ip", "filter", "ids_ban", f'{{ {ip} }}'],
                    check=True
                )
                suspended_ips.remove(ip)
                with ip_suspension_lock:
                    del ip_suspension_time[ip]
            except subprocess.CalledProcessError as e:
                logging.error(f"Erro ao unsuspender IP {ip}: {e}")

# Função para seguir um único arquivo de log
def follow_log(file_path):
    logging.info(f"Iniciando monitoramento do arquivo: {file_path}")
    try:
        with open(file_path, "r") as file:
            file.seek(0, 2)  # Vai para o final do arquivo
            while True:
                line = file.readline()
                if not line:
                    time.sleep(0.1)  # Aguarda se não há novas linhas
                    continue
                process_line(line)
    except Exception as e:
        logging.error(f"Erro ao monitorar o arquivo {file_path}: {e}")

# Função para processar cada linha do log
def process_line(line):
    ip_match = regex_ip.search(line)
    if ip_match:
        ip = ip_match.group(1)
        
        # Contagem de tentativas para /wp-login.php
        if regex_wp_login.search(line):
            with attempts_lock:
                attempts_wp_login[ip] += 1
                count = attempts_wp_login[ip]
            logging.debug(f"IP {ip} tentou /wp-login.php {count} vezes.")
            if count >= 10:
                suspend_ip(ip)
        
        # Contagem de tentativas para 401, 403 ou 404
        elif regex_404.search(line) or regex_403.search(line) or regex_401.search(line):
            with attempts_lock:
                attempts_errors[ip] += 1
                count = attempts_errors[ip]
            logging.debug(f"IP {ip} gerou {count} erros 401/403/404.")
            if count >= 25:
                suspend_ip(ip)

# Função para resetar as tentativas a cada 5 minutos
def reset_attempts():
    while True:
        time.sleep(300)
        with attempts_lock:
            attempts_errors.clear()
            attempts_wp_login.clear()
        logging.info("Resetando contagens de tentativas...")

# Função para limpar IPs suspensos após o período de suspensão
def cleanup_suspended_ips():
    while True:
        time.sleep(60)  # Verifica a cada minuto
        current_time = time.time()
        ips_to_unsuspend = []
        with ip_suspension_lock:
            for ip, suspend_time in list(ip_suspension_time.items()):
                if current_time - suspend_time > suspension_time:
                    ips_to_unsuspend.append(ip)
        
        for ip in ips_to_unsuspend:
            unsuspend_ip(ip)

# Função para monitorar todos os arquivos de log existentes e novos
def monitor_logs():
    monitored_files = set()

    with ThreadPoolExecutor(max_workers=100) as executor:
        # Inicia threads para monitorar os arquivos existentes
        def add_initial_files():
            log_files = glob.glob(os.path.join(log_directory, log_pattern))
            for log_file in log_files:
                if log_file not in monitored_files:
                    executor.submit(follow_log, log_file)
                    monitored_files.add(log_file)
        
        add_initial_files()

        # Inicia threads auxiliares
        executor.submit(reset_attempts)
        executor.submit(cleanup_suspended_ips)
        
        # Monitora continuamente o diretório para novos arquivos de log
        while True:
            time.sleep(10)  # Intervalo para verificar novos arquivos
            log_files = glob.glob(os.path.join(log_directory, log_pattern))
            for log_file in log_files:
                if log_file not in monitored_files:
                    logging.info(f"Novo arquivo de log detectado: {log_file}")
                    executor.submit(follow_log, log_file)
                    monitored_files.add(log_file)
            # Opcional: Remover arquivos que foram deletados
            # arquivos_atualizados = set(glob.glob(os.path.join(log_directory, log_pattern)))
            # arquivos_para_remover = monitored_files - arquivos_atualizados
            # for log_file in arquivos_para_remover:
            #     logging.info(f"Arquivo de log removido: {log_file}")
            #     monitored_files.remove(log_file)

# Execução do script
if __name__ == "__main__":
    try:
        monitor_logs()
    except KeyboardInterrupt:
        logging.info("Monitoramento interrompido pelo usuário.")
