import pyshark
from collections import defaultdict
from collections import namedtuple

# Caminho para o arquivo pcap
pcap_file = 'filtered_traffic.pcap'

# IP de ataque que queremos capturar (use '*' para capturar qualquer IP)
TARGET_IP = '*'  # Ou '144.217.86.46' para o IP de ataque

# Definindo uma estrutura para armazenar o estado das conexões TCP
TCPConnection = namedtuple('TCPConnection', ['src_ip', 'dst_ip', 'src_port', 'dst_port'])

# Função para analisar pacotes
def analyze_pcap(file, target_ip=None):
    # Criação de dicionários para armazenar as informações
    ip_count = defaultdict(int)  # Contagem de pacotes por IP
    protocol_count = defaultdict(int)  # Contagem de pacotes por protocolo
    packet_lengths = []  # Lista para armazenar os tamanhos dos pacotes
    connections = defaultdict(lambda: {'syn_received': False, 'syn_ack_sent': False, 'fin_received': False, 'rst_received': False, 'packets': 0})

    # Abre o arquivo pcap para análise, aplicando filtro de IP, se necessário
    if target_ip != '*':
        cap = pyshark.FileCapture(file, display_filter=f'ip.src == {target_ip} or ip.dst == {target_ip}', use_json=True, keep_packets=False)
    else:
        cap = pyshark.FileCapture(file, use_json=True, keep_packets=False)
    
    # Loop através dos pacotes capturados
    for packet in cap:
        try:
            # Verifique se o pacote tem camada IP e TCP
            if 'IP' in packet and 'TCP' in packet:
                ip_src = packet.ip.src
                ip_dst = packet.ip.dst
                src_port = packet.tcp.srcport
                dst_port = packet.tcp.dstport
                length = int(packet.length)

                # Contagem de pacotes por IP
                ip_count[ip_src] += 1
                ip_count[ip_dst] += 1

                # Conta pacotes por protocolo
                protocol = packet.transport_layer  # Pode ser TCP, UDP, etc.
                protocol_count[protocol] += 1

                # Adiciona o tamanho do pacote à lista
                packet_lengths.append(length)
                
                # Identificando conexões TCP (baseado em IP e portas)
                connection_key = TCPConnection(ip_src, ip_dst, src_port, dst_port)

                # Analisando os pacotes TCP
                if packet.tcp.flags.syn == '1' and packet.tcp.flags.ack == '0':
                    # Pacote SYN enviado (Início da conexão)
                    connections[connection_key]['syn_received'] = True
                elif packet.tcp.flags.syn == '1' and packet.tcp.flags.ack == '1':
                    # Pacote SYN+ACK (Resposta do servidor)
                    connections[connection_key]['syn_ack_sent'] = True
                elif packet.tcp.flags.fin == '1':
                    # Pacote FIN (Finalizando a conexão)
                    connections[connection_key]['fin_received'] = True
                elif packet.tcp.flags.reset == '1':
                    # Pacote RST (Conexão resetada)
                    connections[connection_key]['rst_received'] = True

                # Acompanhando os pacotes na conexão
                if (connections[connection_key]['syn_received'] and
                    connections[connection_key]['syn_ack_sent'] and
                    (connections[connection_key]['fin_received'] or connections[connection_key]['rst_received'])):
                    connections[connection_key]['packets'] += 1

        except AttributeError:
            # Alguns pacotes podem não ter certas informações, ignorar esses casos
            continue
        except Exception as e:
            # Captura de qualquer outro erro inesperado e exibe a mensagem
            print(f"Erro ao processar pacote: {e}")
            continue

    # Exibe os resultados da análise
    print("\nContagem de pacotes por IP:")
    for ip, count in ip_count.items():
        print(f"{ip}: {count} pacotes")

    print("\nContagem de pacotes por protocolo:")
    for protocol, count in protocol_count.items():
        print(f"{protocol}: {count} pacotes")

    print("\nTamanho dos pacotes:")
    if packet_lengths:
        print(f"Média dos tamanhos: {sum(packet_lengths)/len(packet_lengths)} bytes")
        print(f"Tamanho máximo: {max(packet_lengths)} bytes")
        print(f"Tamanho mínimo: {min(packet_lengths)} bytes")
    else:
        print("Nenhum pacote foi analisado.")

    print("\nConexões TCP completas:")
    for connection, data in connections.items():
        if data['syn_received'] and data['syn_ack_sent'] and (data['fin_received'] or data['rst_received']):
            print(f"Conexão {connection.src_ip}:{connection.src_port} <-> {connection.dst_ip}:{connection.dst_port} - {data['packets']} pacotes")

# Chama a função de análise passando o arquivo pcap e o IP de ataque
analyze_pcap(pcap_file, target_ip=TARGET_IP)
