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
    handlers=[logging.FileHandler("log_monitoring.log"), logging.StreamHandler()]
)

# Diretório e padrão de log
log_directory, log_pattern = "/www/wwwlogs", "*access_log"

# Expressões regulares
regex_ip = re.compile(r"^(\d+\.\d+\.\d+\.\d+)")
regex_bots = re.compile(r'semrush|yandex|MJ12bot|babbar.tech|ahrefs.com|DataForSeoBot|SmartReader Library|ClaudeBot|DotBot|Bytespider|SeekportBot')
regex_url = re.compile(r'GET //|POST //|/wp-includes.* 404|/.git|/.env')
regex_wp_login = re.compile(r' /wp-login.php|GPTBot|POST /wp-json/litespeed/v1/cdn_status HTTP/1.1|POST.* 404')
regex_code_status = re.compile(r' (404|403|401|301)')

# Configurações
max_attempts_bots, max_attempts_url, max_attempts_wp_login, max_attempts_code_status = 3, 3, 10, 30
time_window_seconds = 300  # 5 minutos
suspended_ips = set()
attempts = defaultdict(int)
attempts_lock = threading.Lock()

# Suspender IPs no nftables
def suspend_ip(ip, ban_set="ids_ban", regex_used="", trigger=""):
    if ip not in suspended_ips:
        logging.info(f"Suspending IP: {ip} in {ban_set} - Regex: {trigger}")
        try:
            subprocess.run(["sudo", "nft", "add", "element", "ip", "filter", ban_set, f'{{ {ip} }}'], check=True)
            suspended_ips.add(ip)
        except subprocess.CalledProcessError as e:
            logging.error(f"Erro ao suspender IP {ip}: {e}")

# Processar cada linha do log
def process_line(line):
    # Ignorar linhas específicas
    ignored_patterns = ["/g/collect", "/?gad_source", "/assinaturas"]
    for pattern in ignored_patterns:
        if pattern in line:
            logging.debug(f"Linha ignorada: {pattern}")
            return

    ip_match = regex_ip.search(line)
    if not ip_match:
        return
    ip = ip_match.group(1)

    # Itera pelos padrões de regex
    for pattern, count_limit, ban_set, description in [
        (regex_bots, max_attempts_bots, "bots_ban", "Bot detectado"),
        (regex_url, max_attempts_url, "ids_ban", "Acesso proibido detectado"),
        (regex_wp_login, max_attempts_wp_login, "ids_ban", "Detectado Acesso a"),
        (regex_code_status, max_attempts_code_status, "ids_ban", "Erro de status detectado"),
    ]:
        match = pattern.search(line)
        if match:
            with attempts_lock:
                attempts[ip] += 1
                logging.debug(f"IP {ip} - {description}: {match.group(0)}. Contagem: {attempts[ip]}")
                if attempts[ip] >= count_limit:
                    suspend_ip(ip, ban_set, description, trigger=match.group(0))
            return

# Resetar tentativas a cada intervalo
def reset_attempts():
    while True:
        time.sleep(time_window_seconds)
        with attempts_lock:
            attempts.clear()
            suspended_ips.clear()  # Permitir processar IPs suspensos novamente
        logging.info("Resetando contagens de tentativas...")

# Monitorar os arquivos de log
def follow_log(file_path):
    logging.info(f"Iniciando monitoramento do arquivo: {file_path}")
    try:
        with open(file_path, "r") as file:
            file.seek(0, 2)
            while True:
                line = file.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                process_line(line)
    except Exception as e:
        logging.error(f"Erro ao monitorar o arquivo {file_path}: {e}")

# Monitorar arquivos de log existentes e novos
def monitor_logs():
    monitored_files = set()
    with ThreadPoolExecutor(max_workers=100) as executor:
        # Função interna para adicionar arquivos inicialmente e acompanhar novos arquivos
        def add_initial_files():
            for log_file in glob.glob(os.path.join(log_directory, log_pattern)):
                if log_file not in monitored_files:
                    executor.submit(follow_log, log_file)
                    monitored_files.add(log_file)

        add_initial_files()
        executor.submit(reset_attempts)

        # Monitorar novos arquivos
        while True:
            time.sleep(10)
            for log_file in glob.glob(os.path.join(log_directory, log_pattern)):
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
