#!/usr/bin/env python3
import sys
import requests
import os
from datetime import datetime, timezone
from dateutil import parser
import pycountry # Importa a nova biblioteca

# É uma boa prática ler a chave de uma variável de ambiente.
# Defina a variável de ambiente ABUSEIPDB_API_KEY com sua chave.
API_KEY = os.getenv('ABUSEIPDB_API_KEY', 'f0b60dda8b7f5dfde66838df692434e1db04f3ae25589779fd9e1f64df61ce0985377cc30c0e0a58')

def get_country_name(country_code):
    """Converte um código de país (ex: 'BR') para seu nome completo (ex: 'Brazil')."""
    if not country_code:
        return 'Desconhecido'
    try:
        country = pycountry.countries.get(alpha_2=country_code)
        return country.name if country else 'Código inválido'
    except Exception:
        return 'Desconhecido'

def tempo_decorrido(timestamp):
    """Calcula o tempo humano legível desde um timestamp."""
    if not timestamp:
        return 'Nunca reportado'
    try:
        report_time = parser.parse(timestamp)
        agora = datetime.now(timezone.utc)
        delta = agora - report_time

        dias = delta.days
        segundos = delta.seconds
        if dias > 0:
            return f"há {dias} dia{'s' if dias > 1 else ''}"
        elif segundos >= 3600:
            horas = segundos // 3600
            return f"há {horas} hora{'s' if horas > 1 else ''}"
        elif segundos >= 60:
            minutos = segundos // 60
            return f"há {minutos} minuto{'s' if minutos > 1 else ''}"
        else:
            return "há poucos segundos"
    except (parser.ParserError, TypeError):
        return 'Formato inválido'

def consultar_ip(ip):
    """Consulta um endereço IP na API do AbuseIPDB."""
    url = f"https://api.abuseipdb.com/api/v2/check?ipAddress={ip}&maxAgeInDays=90&verbose"
    
    headers = {
        'Accept': 'application/json',
        'Key': API_KEY
    }

    try:
        response = requests.get(url, headers=headers )
        response.raise_for_status()
        
        data = response.json().get('data', {})
        
        if not data:
             return {
                'IP': ip,
                'Último Reporte': 'Não encontrado',
                'País': 'N/A',
                'ISP': 'N/A',
                'Total Reports': 0,
                'Whitelisted': 'N/A'
            }

        # --- CORREÇÃO APLICADA AQUI ---
        # Usamos 'countryCode' e a função get_country_name para obter o país.
        pais = get_country_name(data.get('countryCode'))

        return {
            'IP': data.get('ipAddress', ip),
            'Último Reporte': tempo_decorrido(data.get('lastReportedAt')),
            'País': pais, # Usando a variável corrigida
            'ISP': data.get('isp', 'Desconhecido'),
            'Total Reports': data.get('totalReports', 0),
            'Whitelisted': 'Sim' if data.get('isWhitelisted') else 'Não'
        }
    except requests.exceptions.HTTPError as http_err:
        return {'IP': ip, 'Último Reporte': f'Erro HTTP: {http_err.response.status_code}', 'País': '', 'ISP': '', 'Total Reports': '', 'Whitelisted': ''}
    except Exception as e:
        return {'IP': ip, 'Último Reporte': 'Erro na consulta', 'País': '', 'ISP': '', 'Total Reports': '', 'Whitelisted': str(e )}

# Cabeçalho formatado
print(f"{'IP':<18} {'Último Reporte':<20} {'País':<25} {'ISP':<35} {'Reports':<10} {'Whitelisted'}")
print(f"{'-'*18} {'-'*20} {'-'*25} {'-'*35} {'-'*10} {'-'*11}")

# Lê IPs da entrada padrão (stdin)
for linha in sys.stdin:
    ip = linha.strip()
    if ip:
        resultado = consultar_ip(ip)
        print(f"{str(resultado.get('IP', '')):<18} "
              f"{str(resultado.get('Último Reporte', '')):<20} "
              f"{str(resultado.get('País', '')):<25} "
              f"{str(resultado.get('ISP', '')):<50} "
              f"{str(resultado.get('Total Reports', '')):<10} "
              f"{str(resultado.get('Whitelisted', '')):<11}")
              
# Cabeçalho formatado
print(f"{'IP':<18} {'Último Reporte':<20} {'País':<25} {'ISP':<35} {'Reports':<10} {'Whitelisted':<11}")
print(f"{'-'*18} {'-'*20} {'-'*25} {'-'*35} {'-'*10} {'-'*11}")

# Cabeçalho formatado
print(f"{'IP':<18} {'Último Reporte':<20} {'País':<25} {'ISP':<50} {'Reports':<10} {'Whitelisted':<11}")
print(f"{'-'*18} {'-'*20} {'-'*25} {'-'*50} {'-'*10} {'-'*11}")



