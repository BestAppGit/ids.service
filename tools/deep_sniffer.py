#!/usr/bin/env python3
import subprocess
import time
from collections import defaultdict

def monitor_connections():
    """Monitora novas conexões TCP estabelecidas"""
    print("Iniciando monitoramento de conexões TCP (Ctrl+C para parar)...")
    
    # Dicionário para contar conexões por IP
    ip_count = defaultdict(int)
    total_connections = 0
    
    try:
        while True:
            # Usando 'ss' para obter conexões estabelecidas
            cmd = "ss -tn state established | awk '{print $5}' | cut -d: -f1 | sort | uniq -c"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Processa a saída
                current_ips = set()
                lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
                
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 2:
                        count, ip = int(parts[0]), parts[1]
                        if ip not in ('127.0.0.1', '0.0.0.0') and not ip.startswith(('10.', '192.168.', '172.16.')):
                            ip_count[ip] += count
                            current_ips.add(ip)
                            total_connections += count
                
                # Exibe estatísticas a cada 10 iterações para não poluir o output
                if total_connections % 10 == 0:
                    print(f"\nTotal de conexões: {total_connections}")
                    print(f"IPs únicos detectados: {len(ip_count)}")
                    print("Top 5 IPs por conexões:")
                    for ip, count in sorted(ip_count.items(), key=lambda x: x[1], reverse=True)[:5]:
                        print(f"  {ip}: {count} conexões")
                    print("---")
            
            time.sleep(2)  # Intervalo entre verificações
    
    except KeyboardInterrupt:
        print("\nResumo final:")
        print(f"Total de conexões monitoradas: {total_connections}")
        print(f"Total de IPs únicos detectados: {len(ip_count)}")
        print("\nTop 10 IPs por conexões:")
        for ip, count in sorted(ip_count.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {ip}: {count} conexões")

if __name__ == "__main__":
    monitor_connections()