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
    level=logging.INFO,  # Define o nível de log para INFO
    format='%(asctime)s - %(levelname)s - %(message)s',  # Formato da mensagem de log
    handlers=[
        logging.FileHandler("log_monitoring.log"),  # Salva os logs no arquivo
        logging.StreamHandler()  # Exibe os logs no console
    ]
)


# Diretório contendo os arquivos de log
log_directory = "/www/wwwlogs"
log_pattern = "*access_log"

# Expressões regulares
regex_ip = re.compile(r"^(\d+\.\d+\.\d+\.\d+)")
regex_bots = re.compile(r'semrush|yandex|mj12bot|babbar.tech|ahrefs.com|DataForSeoBot|SmartReader Library|ClaudeBot|DotBot|Bytespider|SeekportBot')
regex_url = re.compile(r'//wp-admin|//wp-login.php|/.git|/.DS_Store |/index.action\\?|\\?rest_route|/.env|/.vscode')
regex_wp_login = re.compile(r' /wp-login.php|GPTBot|POST /wp-json/litespeed/v1/cdn_status HTTP/1.1')
regex_code_status = re.compile(r' (404|403|401|301)')

# Variáveis de configuração
max_attempts_bots = 3
max_attempts_url = 3  # Número máximo de tentativas para a regex_url
max_attempts_wp_login = 10
max_attempts_code_status = 30
time_window_seconds = 300  # 5 minutos de intervalo para contar tentativas

# Conjunto de IPs já suspensos
suspended_ips = set()
suspended_ips_lock = threading.Lock()
bots_ban = set()

# Dicionários para contar tentativas por IP
attempts_errors = defaultdict(int)
attempts_wp_login = defaultdict(int)
attempts_bots = defaultdict(int)
attempts_url = defaultdict(int)  # Dicionário para contar tentativas de acesso a /wp-admin
attempts_lock = threading.Lock()

# Função para adicionar IP ao conjunto 'ids_ban' do nftables
def suspend_ip(ip, ban_set="ids_ban", regex_used=""):
    with suspended_ips_lock:
        if ip not in suspended_ips:
            logging.info(f"Suspending IP: {ip} in {ban_set} - Regex: {regex_used}")
            try:
                subprocess.run(
                    ["sudo", "nft", "add", "element", "ip", "filter", ban_set, f'{{ {ip} }}'],
                    check=True
                )
                suspended_ips.add(ip)
            except subprocess.CalledProcessError as e:
                logging.error(f"Erro ao suspender IP {ip}: {e}")

# Função para processar cada linha do log
def process_line(line):
    # Ignorar linhas que contêm "/g/collect", "/?gad_source" ou "/assinaturas"
    if "/g/collect" in line or "/?gad_source" in line or "/assinaturas" in line:
        logging.debug(f"Ignorando linha com '/g/collect' ou '/?gad_source' ou '/assinaturas': {line.strip()}")
        return  # Ignorar esta linha

    ip_match = regex_ip.search(line)
    if ip_match:
        ip = ip_match.group(1)

        # Contagem de tentativas para bots
        bot_match = regex_bots.search(line)
        if bot_match:
            with attempts_lock:
                attempts_bots[ip] += 1
                count = attempts_bots[ip]
            logging.debug(f"IP {ip} identificado como bot {count} vezes.")
            if count >= max_attempts_bots:
                suspend_ip(ip, ban_set="bots_ban", regex_used=bot_match.group(0))

        # Contagem de tentativas para /wp-admin
        elif regex_url.search(line):
            url_match = regex_url.search(line)
            with attempts_lock:
                attempts_url[ip] += 1
                count = attempts_url[ip]
            logging.debug(f"IP {ip} tentou acessar URLs deny {count} vezes.")
            if count >= max_attempts_url:
                suspend_ip(ip, regex_used=url_match.group(0))

        # Contagem de tentativas para /wp-login.php
        elif regex_wp_login.search(line):
            wp_login_match = regex_wp_login.search(line)
            with attempts_lock:
                attempts_wp_login[ip] += 1
                count = attempts_wp_login[ip]
            logging.debug(f"IP {ip} tentou /wp-login.php {count} vezes.")
            if count >= max_attempts_wp_login:
                suspend_ip(ip, regex_used=wp_login_match.group(0))

        # Contagem de tentativas para 404, 403, 401 e 301
        elif regex_code_status.search(line):
            status_code_match = regex_code_status.search(line)
            with attempts_lock:
                attempts_errors[ip] += 1
                count = attempts_errors[ip]
            logging.debug(f"IP {ip} gerou {count} erros 404/403/401/301.")
            if count >= max_attempts_code_status:
                suspend_ip(ip, regex_used=status_code_match.group(0))

# Função para resetar as tentativas a cada intervalo definido
def reset_attempts():
    while True:
        time.sleep(time_window_seconds)
        with attempts_lock:
            attempts_errors.clear()
            attempts_wp_login.clear()
            attempts_bots.clear()
            attempts_url.clear()  # Limpa as contagens para /wp-admin
        logging.info("Resetando contagens de tentativas...")

# Função para seguir um único arquivo de log
def follow_log(file_path):
    logging.info(f"Iniciando monitoramento do arquivo: {file_path}")
    try:
        with open(file_path, "r") as file:
            file.seek(0, 2)  # Vai para o final do arquivo
            last_size = os.path.getsize(file_path)  # Armazena o tamanho inicial do arquivo

            while True:
                current_size = os.path.getsize(file_path)  # Checa o tamanho atual do arquivo
                
                # Verifica se o arquivo foi rotacionado (tamanho reduzido)
                if current_size < last_size:  # Essa linha verifica se o arquivo foi rotacionado
                    logging.info("Detectada rotação de log. Reabrindo arquivo.")  # Informa que a rotação foi detectada
                    file.close()  # Fecha o arquivo antigo
                    file = open(file_path, "r")  # Reabre o arquivo do início
                    last_size = current_size  # Atualiza o tamanho após reabertura

                line = file.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                
                process_line(line)
                last_size = current_size  # Atualiza o tamanho após leitura
    except Exception as e:
        logging.error(f"Erro ao monitorar o arquivo {file_path}: {e}")

# Função para monitorar todos os arquivos de log existentes e novos
def monitor_logs():
    monitored_files = set()

    with ThreadPoolExecutor(max_workers=100) as executor:
        def add_initial_files():
            log_files = glob.glob(os.path.join(log_directory, log_pattern))
            for log_file in log_files:
                if log_file not in monitored_files:
                    executor.submit(follow_log, log_file)
                    monitored_files.add(log_file)

        add_initial_files()
        executor.submit(reset_attempts)

        while True:
            time.sleep(10)
            log_files = glob.glob(os.path.join(log_directory, log_pattern))
            for log_file in log_files:
                if log_file not in monitored_files:
                    logging.info(f"Novo arquivo de log detectado: {log_file}")
                    executor.submit(follow_log, log_file)
                    monitored_files.add(log_file)

# Execução do script
if __name__ == "__main__":
    try:
        monitor_logs()
    except KeyboardInterrupt:
        logging.info("Monitoramento interrompido pelo usuário.")
