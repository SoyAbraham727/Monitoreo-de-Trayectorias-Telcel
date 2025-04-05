import time
import yaml
import jcs
from concurrent.futures import ThreadPoolExecutor, as_completed
from jnpr.junos import Device
from junos import Junos_Context

# Configuración general
YAML_FILE = "/tmp/resource/trayectorias_telcel.yml"
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
    """Carga el archivo YAML como diccionario."""
    try:
        with open(YAML_FILE, "r") as file:
            return yaml.safe_load(file)
    except yaml.YAMLError as e:
        log_crit(f"Error al leer el YAML: {e}")
    except Exception as e:
        log_crit(f"Error inesperado al leer el YAML: {e}")
    return {}


def guardar_yaml(data):
    """Guarda la información actualizada en el archivo YAML."""
    try:
        with open(YAML_FILE, "w") as file:
            yaml.safe_dump(data, file)
    except Exception as e:
        log_crit(f"Error al escribir el YAML: {e}")


def enviar_alarma(hostname, ip):
    """Envía una alarma después de 3 fallos consecutivos."""
    mensaje = (f"ALARMA: {hostname} con destino {ip} ha fallado durante 15 minutos seguidos")
    log_crit(mensaje)


def hacer_ping(hostname, ip):
    """Ejecuta un ping y determina si hubo degradación."""
    dev = None
    try:
        # Crear una conexión para cada destino
        dev = Device()
        dev.open()

        result = dev.rpc.ping(host=ip, count=str(COUNT))

        enviados = result.findtext("probe-results-summary/probes-sent")
        recibidos = result.findtext("probe-results-summary/responses-received")
        rtt = result.findtext("probe-results-summary/rtt-average")

        if not (enviados and recibidos and rtt):
            log_crit(f"Ping incompleto en {hostname} -> {ip}")
            return False

        enviados = int(enviados.strip())
        recibidos = int(recibidos.strip())
        perdida = enviados - recibidos

        # Convertir rtt de microsegundos a milisegundos
        avg_rtt = float(rtt.strip()) / 1000

        if perdida > MAX_PAQUETES_PERDIDOS or avg_rtt > RTT_THRESHOLD:
            log_warn(f"Degradación en {hostname} -> {ip}: Perdidos={perdida}, RTT={avg_rtt}ms")
            return False

        return True

    except Exception as e:
        log_crit(f"Fallo en ping a {hostname} -> {ip} - Error: {str(e)}")
        return False

    finally:
        if dev:
            dev.close()


def main():
    """Proceso principal de monitoreo."""
    log_crit("Proceso principal de monitoreo.")
    start_time = time.time()  # Registrar el tiempo de inicio

    # Cargar el archivo YAML
    data = cargar_yaml()
    if not data:
        return

    # Obtener el hostname del equipo
    hostname = Junos_Context.get("hostname", "default").split(".")[0]

    # Buscar el hostname en el YAML
    destinos = data[hostname].get(KEY_DESTINOS, [])

    # Obtener los eventos
    eventos_count = data.get(hostname, {}).get(KEY_EVENTOS, 0)

    # Usar ThreadPoolExecutor para ejecutar el ping a cada destino en paralelo
    with ThreadPoolExecutor(max_workers=len(destinos)) as executor:
        futuros = {
            executor.submit(hacer_ping, hostname, ip): ip for ip in destinos
        }
        fallos = []
        for futuro in as_completed(futuros):
            ip = futuros[futuro]
            if not futuro.result():
                fallos.append(ip)

    # Si hay fallos, incrementar eventos y verificar alarma
    if fallos:
        eventos_count += 1
        if eventos_count >= MAX_EVENTOS:
            enviar_alarma(hostname, fallos[0])
            eventos_count = 0
    else:
        eventos_count = 0

    # Actualizar el archivo YAML con el nuevo contador de eventos
    if hostname in data:
        data[hostname][KEY_EVENTOS] = eventos_count

    # Guardar archivo actualizado
    guardar_yaml(data)

    end_time = time.time()  # Registrar el tiempo de finalización
    elapsed_time = end_time - start_time  # Calcular el tiempo transcurrido

    log_warn(f"Finalizó el monitoreo de trayectorias en {elapsed_time:.2f} segundos.")


if __name__ == "__main__":
    main()
