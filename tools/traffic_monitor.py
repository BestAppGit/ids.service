import logging
import pyshark
import mysql.connector
from sklearn.cluster import KMeans
import numpy as np
from time import sleep

# Configuração do log
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuração do banco de dados
DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'traffic_monitor',
    'password': 'PNeZapEfi86tnNWs',
    'database': 'traffic_monitor'
}

# Função para conectar ao banco de dados
def connect_db():
    logging.debug("Tentando conectar ao banco de dados MySQL...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        logging.debug("Conexão estabelecida com sucesso!")
        return conn
    except mysql.connector.Error as err:
        logging.error(f"Erro ao conectar ao MySQL: {err}")
        return None

# Função para capturar pacotes de tráfego
def capture_traffic(interface, interval):
    logging.debug(f"Iniciando captura de pacotes na interface {interface} por {interval} segundos...")
    try:
        capture = pyshark.LiveCapture(interface=interface)
        capture.sniff(timeout=interval)
    except Exception as e:
        logging.error(f"Erro ao capturar pacotes: {e}")
        return None
    
    # Processamento dos pacotes
    traffic_data = {
        'bytes_sent': sum([packet.length for packet in capture if hasattr(packet, 'length')]),
        'bytes_recv': sum([packet.length for packet in capture if hasattr(packet, 'length')]),
        'packets_sent': len([packet for packet in capture]),
        'packets_recv': len([packet for packet in capture]),
    }
    
    # Log dos pacotes capturados
    for packet in capture:
        logging.debug(f"Pacote capturado: {packet}")
        if hasattr(packet, 'ip'):
            logging.debug(f"  IP - Origem: {packet.ip.src}, Destino: {packet.ip.dst}")
        if hasattr(packet, 'tcp'):
            logging.debug(f"  TCP - Porta Origem: {packet.tcp.srcport}, Porta Destino: {packet.tcp.dstport}")
        if hasattr(packet, 'udp'):
            logging.debug(f"  UDP - Porta Origem: {packet.udp.srcport}, Porta Destino: {packet.udp.dstport}")
        if hasattr(packet, 'dns'):
            logging.debug(f"  DNS - Consulta: {packet.dns.qry_name}")
        if hasattr(packet, 'http'):
            logging.debug(f"  HTTP - Requisição: {packet.http.request_method} {packet.http.host}{packet.http.uri}")
    
    logging.debug(f"Tráfego capturado na interface {interface}: {traffic_data}")
    return traffic_data

# Função para treinar o modelo de ML
def train_ml_model(traffic_data_list):
    logging.debug("Treinando modelo de Machine Learning com dados de tráfego...")
    if len(traffic_data_list) < 2:
        logging.debug("Não há dados suficientes para treinar o modelo.")
        return None
    
    # Treinamento do modelo KMeans com múltiplos pontos
    model = KMeans(n_clusters=2)
    try:
        model.fit(np.array(traffic_data_list))
        logging.debug("Modelo treinado com sucesso!")
    except Exception as e:
        logging.error(f"Erro ao treinar modelo: {e}")
        return None
    
    return model

# Função para detectar anomalias
def detect_anomalies(model, traffic_data):
    logging.debug("Detectando anomalias no tráfego...")
    traffic_array = np.array([[traffic_data['bytes_sent'], traffic_data['bytes_recv'],
                               traffic_data['packets_sent'], traffic_data['packets_recv']]])
    
    try:
        # Calculando a distância do ponto ao centro do cluster
        distances = model.transform(traffic_array)
        anomaly_score = np.min(distances)
        logging.debug(f"Pontuação de anomalia (distância mínima ao centro): {anomaly_score}")
        
        if anomaly_score > 0.1:  # Ajuste este limite conforme necessário
            logging.warning(f"Anomalia detectada! Distância: {anomaly_score}")
        else:
            logging.debug("Nenhuma anomalia detectada.")
    
    except Exception as e:
        logging.error(f"Erro ao prever anomalia: {e}")

# Função para inserir dados no banco de dados
def insert_traffic_data_to_db(traffic_data):
    logging.debug("Inserindo dados no banco de dados...")
    conn = connect_db()
    if conn is not None:
        cursor = conn.cursor()
        insert_query = """
        INSERT INTO traffic_data (bytes_sent, bytes_recv, packets_sent, packets_recv)
        VALUES (%s, %s, %s, %s)
        """
        data = (traffic_data['bytes_sent'], traffic_data['bytes_recv'],
                traffic_data['packets_sent'], traffic_data['packets_recv'])
        
        try:
            cursor.execute(insert_query, data)
            conn.commit()
            logging.debug("Dados inseridos com sucesso no banco!")
        except mysql.connector.Error as err:
            logging.error(f"Erro ao inserir dados no banco: {err}")
        finally:
            cursor.close()
            conn.close()

# Função principal para monitorar o tráfego
def monitor_traffic():
    logging.debug("Iniciando monitoramento de tráfego...")
    interface = 'lo'  # Substitua pela sua interface de rede
    interval = 1  # Intervalo para capturar tráfego, em segundos
    
    # Verificar se a interface de rede está disponível
    try:
        capture = pyshark.LiveCapture(interface=interface)
    except Exception as e:
        logging.error(f"Erro ao acessar a interface {interface}: {e}")
        return
    
    # Lista para acumular dados de tráfego
    traffic_data_list = []
    
    # Loop para capturar e processar os pacotes
    while True:
        traffic_data = capture_traffic(interface, interval)
        if traffic_data:
            traffic_data_list.append([traffic_data['bytes_sent'], traffic_data['bytes_recv'],
                                      traffic_data['packets_sent'], traffic_data['packets_recv']])
            
            # Treinamento do modelo quando houver dados suficientes
            if len(traffic_data_list) >= 10:  # Exemplo de 10 pontos de dados
                model = train_ml_model(traffic_data_list)
                if model:
                    # Detecção de anomalias
                    detect_anomalies(model, traffic_data)
                
            # Inserção de dados no banco de dados
            insert_traffic_data_to_db(traffic_data)
        
        sleep(10)  # Aguardar 10 segundos antes de capturar novamente

# Loop para rodar o monitoramento constantemente
if __name__ == '__main__':
    while True:
        try:
            monitor_traffic()
        except KeyboardInterrupt:
            logging.info("Captura de tráfego interrompida.")
            break
