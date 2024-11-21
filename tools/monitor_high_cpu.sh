#!/bin/bash

# Arquivo para salvar os logs
LOG_FILE="/var/log/high_cpu_processes.log"

# Frequência de verificação em segundos
INTERVAL=5

# Função para monitorar e registrar processos com alto uso de CPU
monitor_processes() {
    while true; do
        # Captura os processos usando mais de 90% de CPU
        top -b -n 1 | awk '$9 >= 90 {print strftime("%Y-%m-%d %H:%M:%S"), $0}' >> "$LOG_FILE"
        sleep "$INTERVAL"
    done
}

# Executa o monitoramento
monitor_processes
