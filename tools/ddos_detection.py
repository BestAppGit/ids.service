import os
import re
from collections import defaultdict

# Caminho para o diretório de logs
LOG_DIRECTORY = '/www/wwwlogs'

# Padrões de regex para detectar anomalias
regex_bots = r"bot|crawler|spider|curl|wget|python|perl|java|libwww|nmap|nujie|httrack"
regex_url = r"\/wp-login.php|\/xmlrpc.php|\/admin|\/cgi-bin|\/phpmyadmin"
regex_ip = r"(\d+\.\d+\.\d+\.\d+|[a-fA-F0-9:]+)"  # IPv4 e IPv6

# Função para analisar os logs
def analyze_logs():
    suspicious_ips = defaultdict(int)
    suspicious_patterns = defaultdict(int)

    # Varre todos os arquivos de log no diretório especificado
    for log_file in os.listdir(LOG_DIRECTORY):
        log_path = os.path.join(LOG_DIRECTORY, log_file)
        
        # Ignora diretórios e arquivos não relacionados
        if not os.path.isfile(log_path):
            continue
        
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as file:
                for log in file:
                    ip_address = extract_ip(log)
                    if ip_address:
                        # Contagem de IPs suspeitos
                        suspicious_ips[ip_address] += 1

                    # Verifica padrões suspeitos (bots, urls, etc.)
                    check_patterns(log, suspicious_patterns)
        except Exception as e:
            print(f"Erro ao processar o arquivo {log_file}: {e}")

    # Exibe os IPs suspeitos
    print("\nIPs suspeitos:")
    for ip, count in suspicious_ips.items():
        print(f"IP: {ip}, Requests: {count}")

    # Exibe os padrões maliciosos encontrados nos logs
    print("\nPadrões maliciosos encontrados:")
    for pattern, count in suspicious_patterns.items():
        print(f"Pattern: {pattern}, Count: {count}")

# Função para extrair o IP do log
def extract_ip(log):
    match = re.search(regex_ip, log)
    if match:
        return match.group(1)
    return None

# Função para verificar os padrões maliciosos no log
def check_patterns(log, suspicious_patterns):
    # Verifica por bots
    if re.search(regex_bots, log, re.IGNORECASE):
        suspicious_patterns["bot detected"] += 1
    
    # Verifica por URLs suspeitas
    if re.search(regex_url, log):
        suspicious_patterns["suspicious URL detected"] += 1

# Executa a análise dos logs
if __name__ == "__main__":
    analyze_logs()
