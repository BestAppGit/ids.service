import os
from collections import defaultdict

# Função para verificar se a URL deve ser ignorada
def should_ignore_url(url):
    return '/g/' in url or 'google' in url

# Função para calcular a pontuação com base na quantidade de ocorrências
def calculate_score(count):
    return count * 30  # ou qualquer outra lógica que faça sentido para o seu caso

# Função para truncar a URL se for muito longa
def truncate_url(url, max_length=60):
    return (url[:max_length] + '...') if len(url) > max_length else url

# Diretório onde os logs estão
log_dir = '/www/wwwlogs'

# Dicionário para armazenar os padrões maliciosos
patterns = defaultdict(int)

# Leitura e análise dos logs
total_lines = 0
ignored_lines = 0

for log_file in os.listdir(log_dir):
    log_path = os.path.join(log_dir, log_file)
    with open(log_path, 'r') as file:
        for line in file:
            total_lines += 1

            # Dividir a linha em partes
            parts = line.split(' ')
            if len(parts) >= 11:  # Verifica se há partes suficientes
                ip = parts[0]
                url = parts[6]  # O caminho da URL geralmente está na posição 6
                status = parts[8]  # O código de status geralmente está na posição 8
                referer = parts[10].strip('\"')  # O referer geralmente está na posição 10

                if should_ignore_url(url):
                    ignored_lines += 1
                    continue

                patterns[(ip, url, status, referer)] += 1
            else:
                ignored_lines += 1

# Preparar os dados para exibição
results = []
for (ip, url, status, referer), count in patterns.items():
    score = calculate_score(count)
    # Truncar a URL se for muito longa
    truncated_url = truncate_url(url)
    # Truncar o referer se for muito longo
    truncated_referer = truncate_url(referer)
    # Adicionar resultado como string única com delimitadores
    results.append(f"{ip:<15} {truncated_url:<60} {status:<5} {count:<10} {score:<10} {truncated_referer:<60}")

# Ordenar os padrões por quantidade de ocorrências (descendente)
results.sort(key=lambda x: int(x.split()[3]), reverse=True)

# Exibir resultados em uma única linha por padrão malicioso
if results:
    print(f"{'IP':<15} {'URL Truncada':<60} {'Status':<5} {'Qtd':<10} {'Pontuação':<10} {'Referer Truncado':<60}")
    print("=" * 150)  # Linha de separação
    for result in results:
        print(result)
else:
    print("Nenhum padrão malicioso foi encontrado para análise.")

# Exibir estatísticas gerais
print(f"\nTotal de arquivos lidos: {len(os.listdir(log_dir))}")
print(f"Total de linhas lidas: {total_lines}")
print(f"Total de logs ignorados: {ignored_lines}")
