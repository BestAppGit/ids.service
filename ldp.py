#!/usr/bin/env python3
import os
import time
import logging
import subprocess
import argparse
import threading
from datetime import datetime

# Configurações
SERVER_LOAD_THRESHOLD = 10
LOAD_CHECK_INTERVAL = 1
LOG_NORMAL_INTERVAL = 300
LOG_HIGH_LOAD_INTERVAL = 3
PROCESS_STABLE_CHECKS = 5
WAIT_AFTER_RESTART = 30  # 30 segundos de espera após reinício

def setup_logging(debug=False):
    """Configura o sistema de logging"""
    level = logging.DEBUG if debug else logging.INFO
    
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%d/%b/%Y:%H:%M:%S"
    )
    
    # Handlers
    fh = logging.FileHandler("ldp_monitoring.log")
    fh.setFormatter(formatter)
    
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    
    logging.basicConfig(level=level, handlers=[fh, ch])


def parse_arguments():
    """Interpreta argumentos da linha de comando"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="Ativa logs DEBUG detalhados")
    return parser.parse_args()

def get_server_load():
    """Obtém a carga média do sistema (1 minuto)"""
    try:
        load = os.getloadavg()[0]
        if logging.getLogger().level == logging.DEBUG:
            logging.debug(f"Carga atual: {load:.2f}")
        return load
    except Exception as e:
        logging.error(f"Falha ao medir carga: {str(e)}")
        return 0.0

def stop_web_services():
    """Para serviços web e processos relacionados"""
    try:
        logging.error("Alta carga detectada! Parando serviços...")
        subprocess.run(["systemctl", "stop", "lsws.service"], check=True)
        subprocess.run(["killall", "lsphp"], check=True)
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Falha ao parar serviços: {str(e)}")
        return False

def save_process_snapshot(debug=False):
    """Registra snapshot dos processos lsphp no log"""
    try:
        result = subprocess.run(
            ["pgrep", "-a", "lsphp"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0 or not result.stdout.strip():
            logging.warning("Nenhum processo lsphp encontrado")
            return

        for line in result.stdout.strip().splitlines():
            logging.warning(f"Comando: {line}")

        if debug:
            logging.debug("Snapshot de processos lsphp registrado no log")

    except Exception as e:
        logging.error(f"Erro ao salvar snapshot: {str(e)}")

def monitor_php_processes():
    """Monitora processos lsphp até estabilização, gerando snapshots do ps"""
    logging.info("Monitorando processos lsphp...")

    stable_checks = 0
    while stable_checks < PROCESS_STABLE_CHECKS:
        try:
            # Conta processos lsphp
            result = subprocess.run(
                ["sh", "-c", "pgrep lsphp | wc -l"],
                capture_output=True,
                text=True
            )
            count = int(result.stdout.strip())
            logging.info(f"Processos lsphp ativos: {count}")

            if count <= 1:
                stable_checks += 1
            else:
                stable_checks = 0

            # Snapshot do pgrep
            save_process_snapshot()

        except Exception as e:
            logging.error(f"Erro no monitoramento: {str(e)}")
            return False

        time.sleep(LOG_HIGH_LOAD_INTERVAL)

    return True

def snapshot_top_loop():
    """Gera snapshots do ps a cada 3 segundos (modo DEBUG)"""
    while True:
        save_process_snapshot(debug=True)
        time.sleep(5)

def restart_services():
    """Reinicia serviços web com confirmação"""
    try:
        logging.info("Reiniciando serviços...")
        subprocess.run(["systemctl", "start", "lsws.service"], check=True)
        subprocess.run(["systemctl", "restart", "ids.service"], check=True)
        logging.info("Serviços reiniciados com sucesso")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Falha ao reiniciar serviços: {str(e)}")
        return False

def handle_high_load():
    """Executa fluxo completo para alta carga"""
    if not stop_web_services():
        return False
    
    if not monitor_php_processes():
        return False
    
    if restart_services():
        logging.info(f"Aguardando {WAIT_AFTER_RESTART} segundos antes de retomar monitoramento...")
        time.sleep(WAIT_AFTER_RESTART)
        logging.info("Monitoramento reiniciado")
        return True
    
    return False

def main():
    args = parse_arguments()
    setup_logging(args.debug)
    
    logging.info("Iniciando monitoramento do servidor")

    # Thread de snapshots contínuos em DEBUG
    if args.debug:
        t = threading.Thread(target=snapshot_top_loop, daemon=True)
        t.start()

    last_log = time.time()
    
    while True:
        load = get_server_load()
        
        if load >= SERVER_LOAD_THRESHOLD:
            handle_high_load()
            last_log = time.time()
        elif time.time() - last_log >= LOG_NORMAL_INTERVAL:
            logging.info("Carga normal nos últimos 5 minutos")
            last_log = time.time()
            
        time.sleep(LOAD_CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Monitoramento encerrado")
    except Exception as e:
        logging.error(f"Falha crítica: {str(e)}")
