import psutil
import time
import subprocess
import logging

# Configuração do log
logging.basicConfig(filename='server_protection.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# Função para verificar a carga de 1 minuto do sistema
def get_load_average():
    return psutil.getloadavg()[0]  # Retorna o load average de 1 minuto

# Função para executar comandos do sistema com log de erro detalhado
def execute_command(command):
    try:
        subprocess.run(command, shell=True, check=True)
        logging.info(f"Comando executado com sucesso: {command}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Erro ao executar '{command}': {e}")

# Função principal de monitoramento e proteção
def monitor_and_protect():
    high_load_start_time = None  # Marca o início do período de alta carga
    max_restart_attempts = 3     # Máximo de tentativas para reiniciar os serviços
    restart_attempts = 0         # Contador de tentativas de reinício

    while True:
        load_avg = get_load_average()
        logging.info(f"Carga de 1 minuto atual: {load_avg}")

        # Verifica se a carga está acima de 5
        if load_avg > 5:
            # Inicia o contador se for a primeira detecção de alta carga
            if high_load_start_time is None:
                high_load_start_time = time.monotonic()
                logging.info("Alta carga detectada, iniciando contagem")

            # Verifica se a alta carga dura mais de 60 segundos
            elif time.monotonic() - high_load_start_time >= 60:
                logging.warning("Alto consumo de recursos detectado por 60 segundos, acionando proteção")

                # Ações de proteção
                execute_command("killall lsphp")
                execute_command("service lshttpd stop")
                logging.info("Serviços interrompidos para reduzir carga")

                # Aguarda até a carga cair abaixo de 2 para reiniciar os serviços
                while get_load_average() >= 2:
                    logging.info("Aguardando a carga reduzir abaixo de 2 para reiniciar os serviços")
                    time.sleep(5)

                # Reinicia os serviços com limite de tentativas
                while restart_attempts < max_restart_attempts:
                    logging.info("Carga reduzida, tentando reiniciar serviços de IDS e LiteSpeed")
                    execute_command("systemctl start lshttpd")
                    execute_command("systemctl restart ids.service")

                    # Verifica se a carga permanece estável após a reinicialização
                    time.sleep(5)  # Aguardar alguns segundos para estabilizar a carga
                    if get_load_average() < 2:
                        logging.info("Serviços reiniciados com sucesso e carga estabilizada")
                        break
                    else:
                        restart_attempts += 1
                        logging.warning(f"Falha ao reiniciar serviços. Tentativa {restart_attempts} de {max_restart_attempts}")
                
                # Se exceder o número máximo de tentativas, registrar aviso
                if restart_attempts >= max_restart_attempts:
                    logging.error("Falha ao estabilizar os serviços após múltiplas tentativas")

                # Reseta o contador e o temporizador após as ações de proteção
                high_load_start_time = None
                restart_attempts = 0

        else:
            # Reseta o contador de alta carga e reinicia o temporizador se a carga estiver abaixo de 5
            high_load_start_time = None

        time.sleep(5)  # Checa a cada 5 segundos

# Inicia o monitoramento constante
if __name__ == "__main__":
    logging.info("Iniciando monitoramento de carga do servidor")
    monitor_and_protect()
