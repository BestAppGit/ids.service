#!/usr/bin/env python3
import os
import time
import logging
import subprocess
import argparse  # Adicionado para suporte a argumentos
from datetime import datetime, timedelta

# Configurações
SERVER_LOAD_THRESHOLD = 10.0
LOAD_CHECK_INTERVAL = 1
LOG_NORMAL_INTERVAL = 300
LOG_HIGH_LOAD_INTERVAL = 3
PROCESS_STABLE_CHECKS = 5

def setup_logging(debug=False):
    """Configura o sistema de logging baseado no modo debug"""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("ldp_monitoring.log"),
            logging.StreamHandler()
        ]
    )

def parse_arguments():
    """Configura e interpreta argumentos da linha de comando"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="Ativa modo DEBUG detalhado")
    return parser.parse_args()

def get_server_load():
    """Retorna a carga média do servidor (1 min)."""
    try:
        return os.getloadavg()[0]
    except Exception as e:
        logging.error(f"Erro ao obter carga: {str(e)}")
        return 0.0

# ... (outras funções permanecem idênticas) ...

def main():
    args = parse_arguments()
    setup_logging(debug=args.debug)
    
    if args.debug:
        logging.debug("Modo DEBUG ativado - Logs detalhados habilitados")
    
    last_normal_log = time.time()
    logging.info("Script iniciado - Monitoramento ativo")

    while True:
        current_load = get_server_load()
        current_time = time.time()

        if logging.getLogger().level == logging.DEBUG:
            logging.debug(f"Carga atual: {current_load:.2f}")

        if current_load >= SERVER_LOAD_THRESHOLD:
            monitor_high_load()
            last_normal_log = time.time()
        elif current_time - last_normal_log >= LOG_NORMAL_INTERVAL:
            logging.info("Carga normal nos últimos 5 minutos")
            last_normal_log = current_time

        time.sleep(LOAD_CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Script encerrado pelo usuário")
    except Exception as e:
        logging.error(f"ERRO CRÍTICO: {str(e)}")