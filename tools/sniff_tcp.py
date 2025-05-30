from scapy.all import sniff, TCP, IP
import ipaddress

INTERFACE = "eth0"  # Altere para sua interface pública real

def is_syn(pkt):
    return TCP in pkt and pkt[TCP].flags == "S"

def is_public(ip):
    try:
        return ipaddress.ip_address(ip).is_global
    except ValueError:
        return False

def handle_packet(pkt):
    if is_syn(pkt):
        ip = pkt[IP].src
        if is_public(ip):
            print(f"Nova conexão TCP de IP público: {ip}")

print(f"Escutando conexões TCP (SYN) em {INTERFACE}... Pressione Ctrl+C para sair.")
sniff(filter="tcp", iface=INTERFACE, prn=handle_packet, store=0)
