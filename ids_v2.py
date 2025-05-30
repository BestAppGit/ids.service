import re
import subprocess
import time
import glob
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import logging
import os
import sys

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
regex_bots = re.compile(r'semrush|yandex|MJ12bot|babbar.tech|ahrefs.com|DataForSeoBot|ClaudeBot|DotBot|Bytespider|SeekportBot')
regex_url = re.compile(r'GET //|POST //|/wp-includes.* 404|/\.git|/\.env|/wp-login.* 404')
regex_wp_login = re.compile(r' /wp-login.php|GPTBot|/wp-json/litespeed/v1/cdn_status|POST.* 404|HEAD')
regex_code_status = re.compile(r' (404|403|401|301)')

# Configurações
max_attempts_bots, max_attempts_url, max_attempts_wp_login, max_attempts_code_status = 3, 3, 10, 50
time_window_seconds = 300  # 5 minutos
suspended_ips = set()
attempts = defaultdict(int)
attempts_lock = threading.Lock()

# --- FUNÇÕES MODIFICADAS PARA SUBNET /24 ---
def get_subnet_24(ip):
    """Retorna a sub-rede /24 do IP (ex: 192.168.1.0/24)."""
    return ".".join(ip.split(".")[:3]) + ".0/24"

def suspend_ip(ip, ban_set="ids_ban", regex_used="", trigger=""):
    """Bloqueia a sub-rede /24 do IP no nftables."""
    subnet_24 = get_subnet_24(ip)
    if subnet_24 not in suspended_ips:
        logging.info(f"Suspending Subnet: {subnet_24} in {ban_set} - Regex: {trigger}")
        try:
            subprocess.run(["sudo", "nft", "add", "element", "ip", "filter", ban_set, f'{{ {subnet_24} }}'], check=True)
            suspended_ips.add(subnet_24)
        except subprocess.CalledProcessError as e:
            logging.error(f"Erro ao suspender Subnet {subnet_24}: {e}")

# --- PROCESSAMENTO DE LINHAS (AGORA CONTA POR SUBNET) ---
def process_line(line):
    # Ignorar linhas específicas
    ignored_patterns = ["/g/collect", "/?gad_source", "/assinaturas", "woocommerce_task_list", "/wordpress-seo-premium"]
    for pattern in ignored_patterns:
        if pattern in line:
            logging.debug(f"Linha ignorada: {pattern}")
            return

    ip_match = regex_ip.search(line)
    if not ip_match:
        return
    ip = ip_match.group(1)
    subnet_24 = get_subnet_24(ip)  # Obtém a sub-rede /24

    # Verifica padrões e incrementa contagem por subnet
    for pattern, count_limit, ban_set, description in [
        (regex_bots, max_attempts_bots, "bots_ban", "Bot detectado"),
        (regex_url, max_attempts_url, "ids_ban", "Acesso proibido detectado"),
        (regex_wp_login, max_attempts_wp_login, "ids_ban", "Detectado Acesso a"),
        (regex_code_status, max_attempts_code_status, "ids_ban", "Erro de status detectado"),
    ]:
        match = pattern.search(line)
        if match:
            with attempts_lock:
                attempts[subnet_24] += 1  # Contagem por subnet
                logging.debug(f"Subnet {subnet_24} - {description}: {match.group(0)}. Contagem: {attempts[subnet_24]}")
                if attempts[subnet_24] >= count_limit:
                    suspend_ip(ip, ban_set, description, trigger=match.group(0))
            return

# --- FUNÇÕES ORIGINAIS (MANTIDAS) ---
def reset_attempts():
    while True:
        time.sleep(time_window_seconds)
        with attempts_lock:
            attempts.clear()
            suspended_ips.clear()
        logging.info("Resetando contagens de tentativas...")

def follow_log(file_path):
    logging.debug(f"Iniciando monitoramento do arquivo: {file_path}")
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

def monitor_logs():
    monitored_files = set()
    with ThreadPoolExecutor(max_workers=100) as executor:
        def add_initial_files():
            for log_file in glob.glob(os.path.join(log_directory, log_pattern)):
                if log_file not in monitored_files:
                    executor.submit(follow_log, log_file)
                    monitored_files.add(log_file)

        add_initial_files()
        executor.submit(reset_attempts)

        while True:
            time.sleep(10)
            for log_file in glob.glob(os.path.join(log_directory, log_pattern)):
                if log_file not in monitored_files:
                    logging.info(f"Novo arquivo de log detectado: {log_file}")
                    executor.submit(follow_log, log_file)
                    monitored_files.add(log_file)

def restart_script_periodically():
    while True:
        time.sleep(3600)
        logging.info("Reiniciando o script...")
        os.execv(sys.executable, [sys.executable] + sys.argv)

# --- INÍCIO DO SCRIPT ---
if __name__ == "__main__":
    threading.Thread(target=restart_script_periodically, daemon=True).start()
    try:
        monitor_logs()
    except KeyboardInterrupt:
        logging.info("Monitoramento interrompido pelo usuário.")