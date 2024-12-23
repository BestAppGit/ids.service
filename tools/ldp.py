import psutil
import time
import subprocess
import logging
from datetime import datetime

# Configuração do log com o formato solicitado
logging.basicConfig(filename='server_protection.log', level=logging.INFO,
                    format='%(asctime)s - %(message)s')

# Função para verificar a carga de 1 minuto do sistema
def get_load_average():
    return psutil.getloadavg()[0]  # Retorna o load average de 1 minuto

# Função para executar comandos do sistema com log de erro detalhado
def execute_command(command):
    try:
        subprocess.run(command, shell=True, check=True)
        logging.info(f"Comando executado: {command}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Erro ao executar '{command}': {e}")

# Função principal de monitoramento e proteção
def monitor_and_protect():
    high_load_start_time = None
    max_restart_attempts = 3
    restart_attempts = 0

    while True:
        load_avg = get_load_average()
        logging.debug(f"Carga de 1 minuto atual: {load_avg}")

        if load_avg > 8:
            if high_load_start_time is None:
                high_load_start_time = time.monotonic()
                logging.info("Alta carga detectada, iniciando contagem")
            elif time.monotonic() - high_load_start_time >= 120:
                logging.warning("Alta carga por 2 minutos, acionando proteção")
                execute_command("killall lsphp")
                execute_command("service lshttpd stop")

                while get_load_average() >= 2:
                    logging.info("Aguardando carga reduzir abaixo de 2")
                    time.sleep(5)

                while restart_attempts < max_restart_attempts:
                    logging.info("Tentando reiniciar serviços")
                    execute_command("systemctl start lshttpd")
                    execute_command("systemctl restart ids.service")

                    time.sleep(5)
                    if get_load_average() < 2:
                        logging.info("Serviços reiniciados com sucesso")
                        break
                    else:
                        restart_attempts += 1
                        logging.warning(f"Falha ao reiniciar, tentativa {restart_attempts}")

                if restart_attempts >= max_restart_attempts:
                    logging.error("Falha ao estabilizar serviços após múltiplas tentativas")

                high_load_start_time = None
                restart_attempts = 0
        else:
            high_load_start_time = None

        time.sleep(5 if load_avg < 5 else 2)

if __name__ == "__main__":
    logging.info("Iniciando monitoramento de carga do servidor")
    monitor_and_protect()