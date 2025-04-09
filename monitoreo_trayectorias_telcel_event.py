import time
import yaml
import jcs
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from junos import Junos_Context

# Configuración general
YAML_FILE = "/tmp/trayectorias_telcel.yml"  # Ruta persistente
COUNT = 20  # Cantidad de paquetes a enviar
RTT_THRESHOLD = 100  # ms
MAX_EVENTOS = 3
MAX_PAQUETES_PERDIDOS = 0

# Claves YAML
KEY_DESTINOS = "destinos"
KEY_EVENTOS = "eventos"

# Severidad de logs
CRITICAL_SEVERITY = "external.crit"
WARNING_SEVERITY = "external.warn"

def log_crit(msg):
    jcs.syslog(CRITICAL_SEVERITY, msg)

def log_warn(msg):
    jcs.syslog(WARNING_SEVERITY, msg)

def cargar_yaml():
    try:
        with open(YAML_FILE, "r") as file:
            return yaml.safe_load(file)
    except yaml.YAMLError as e:
        log_crit(f"Error al leer el YAML: {e}")
    except Exception as e:
        log_crit(f"Error inesperado al leer el YAML: {e}")
    return {}

def guardar_yaml(data):
    try:
        with open(YAML_FILE, "w") as file:
            yaml.safe_dump(data, file)
    except Exception as e:
        log_crit(f"Error al escribir el YAML: {e}")

def enviar_alarma(hostname, ip):
    mensaje = f"ALARMA: {hostname} con destino {ip} ha fallado durante 15 minutos seguidos"
    log_crit(mensaje)

def parsear_ping(output):
    """Extrae la cantidad de paquetes perdidos y RTT promedio desde el resultado de jcs.run()."""
    try:
        perdida = 0
        rtt = 0.0

        # Buscar línea con "packet loss"
        match_perdida = re.search(r'(\d+) packets transmitted, (\d+) packets received', output)
        if match_perdida:
            enviados = int(match_perdida.group(1))
            recibidos = int(match_perdida.group(2))
            perdida = enviados - recibidos
        else:
            return None, None

        # Buscar línea con "round-trip"
        match_rtt = re.search(r'round-trip.* = ([\d\.]+)/', output)
        if match_rtt:
            rtt = float(match_rtt.group(1))
        else:
            return None, None

        return perdida, rtt

    except Exception as e:
        log_crit(f"Error al parsear el resultado del ping: {e}")
        return None, None

def hacer_ping(hostname, ip):
    try:
        output = jcs.run(f"ping {ip} count {COUNT}")
        if not output:
            log_crit(f"Error: no hubo respuesta del ping para {ip}")
            return False

        perdida, rtt = parsear_ping(output)
        if perdida is None or rtt is None:
            log_crit(f"Ping inválido para {ip}")
            return False

        if perdida > MAX_PAQUETES_PERDIDOS or rtt > RTT_THRESHOLD:
            log_warn(f"Degradación en {hostname} -> {ip}: Perdidos={perdida}, RTT={rtt}ms")
            return False

        return True

    except Exception as e:
        log_crit(f"Fallo en ping a {hostname} -> {ip} - Error: {str(e)}")
        return False

def main():
    log_warn("Inicio del monitoreo de trayectorias")
    start_time = time.time()

    data = cargar_yaml()
    if not data:
        return

    hostname = Junos_Context.get("hostname", "default").split(".")[0]

    if hostname not in data:
        log_warn(f"Hostname '{hostname}' no encontrado en YAML, usando 'default'.")
        hostname = "default"

    destinos = data[hostname].get(KEY_DESTINOS, [])
    eventos_count = data[hostname].get(KEY_EVENTOS, 0)

    with ThreadPoolExecutor(max_workers=len(destinos)) as executor:
        futuros = {executor.submit(hacer_ping, hostname, ip): ip for ip in destinos}
        fallos = []
        for futuro in as_completed(futuros):
            ip = futuros[futuro]
            if not futuro.result():
                fallos.append(ip)

    if fallos:
        eventos_count += 1
        if eventos_count >= MAX_EVENTOS:
            enviar_alarma(hostname, fallos[0])
            eventos_count = 0
    else:
        eventos_count = 0

    data[hostname][KEY_EVENTOS] = eventos_count
    guardar_yaml(data)

    elapsed_time = time.time() - start_time
    log_warn(f"Finalizó el monitoreo en {elapsed_time:.2f} segundos.")

if __name__ == "__main__":
    main()
