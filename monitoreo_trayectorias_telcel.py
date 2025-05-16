import time
import yaml
import jcs
from concurrent.futures import ThreadPoolExecutor, as_completed
from jnpr.junos import Device
from junos import Junos_Context


# Configuracion general
YAML_FILE = "/tmp/gsop/scripts/trayectorias_telcel.yml" 
COUNT = 20
RTT_THRESHOLD = 100
MAX_EVENTOS = 2
MAX_PAQUETES_PERDIDOS = 4


# Claves YAML
KEY_DESTINOS = "destinos"


# Severidad de logs
WARNING_SEVERITY = "external.crit"


def log_warn(msg):
    jcs.syslog(WARNING_SEVERITY, msg)


def cargar_yaml():
    """Carga el archivo YAML como diccionario."""
    try:
        with open(YAML_FILE, "r") as file:
            return yaml.safe_load(file)
    except yaml.YAMLError as e:
        log_warn(f"Error al leer el YAML: {e}")
    except Exception as e:
        log_warn(f"Error inesperado al leer el YAML: {e}")
    return {}


def guardar_yaml(data):
    """Guarda la informacion actualizada en el archivo YAML."""
    try:
        with open(YAML_FILE, "w") as file:
            yaml.safe_dump(data, file)
    except Exception as e:
        log_warn(f"Error al escribir el YAML: {e}")


def enviar_alarma(hostname, ip):
    """Envia una alarma despues de 3 fallos consecutivos."""
    mensaje = (f"%ONBOX-TELCEL-4-DEGRADATION : Se detecto degradacion de servicio en el equipo {hostname} con destino {ip}")
    log_warn(mensaje)


def hacer_ping(hostname, ip):
    """Ejecuta un ping y determina si hubo degradacion."""
    dev = None
    try:
        # Crear una conexion para cada destino
        dev = Device()
        dev.open()

        result = dev.rpc.ping(host=ip, count=str(COUNT))

        enviados = result.findtext("probe-results-summary/probes-sent")
        recibidos = result.findtext("probe-results-summary/responses-received")
        rtt = result.findtext("probe-results-summary/rtt-average")

        if not (enviados and recibidos and rtt):
            log_warn(f"Ping incompleto en {hostname} -> {ip}")
            return False

        enviados = int(enviados.strip())
        recibidos = int(recibidos.strip())
        perdida = enviados - recibidos

        # Convertir rtt de microsegundos a milisegundos
        avg_rtt = float(rtt.strip()) / 1000

        if perdida > MAX_PAQUETES_PERDIDOS or avg_rtt > RTT_THRESHOLD:
            log_warn(f"Degradacion en {hostname} -> {ip}: Perdidos={perdida}, RTT={avg_rtt}ms")
            return False

        return True

    except Exception as e:
        log_warn(f"Fallo en ping a {hostname} -> {ip} - Error: {str(e)}")
        return False

    finally:
        if dev:
            dev.close()


def main():
    """Proceso principal de monitoreo."""
    log_warn("Proceso principal de monitoreo.")
    start_time = time.time() 

    # Cargar el archivo YAML
    data = cargar_yaml()
    if not data:
        return

    # Obtener el hostname del equipo
    hostname = Junos_Context.get("hostname", "default").split(".")[0]

    #Verificar si el hostname está presente como clave en el archivo YAML
    if hostname not in data:
        log_warn(f"Hostname '{hostname}' no encontrado en el archivo YAML, asignando 'default'.")
        hostname = "default"

    # Buscar el hostname en el YAML
    destinos = data[hostname].get(KEY_DESTINOS, {})

    with ThreadPoolExecutor(max_workers=len(destinos)) as executor:
        futuros = {executor.submit(hacer_ping, hostname, ip): ip for ip in destinos}

        for futuro in as_completed(futuros):
            ip = futuros[futuro]
            exito = futuro.result()

            if not exito:
                destinos[ip] += 1
                if destinos[ip] >= MAX_EVENTOS:
                    enviar_alarma(hostname, ip)
                    destinos[ip] = 0
            else:
                destinos[ip] = 0


    # Guardar archivo actualizado
    guardar_yaml({hostname: {KEY_DESTINOS: destinos}})

    end_time = time.time()
    elapsed_time = end_time - start_time

    log_warn(f"Finalizo el monitoreo de trayectorias en {elapsed_time:.2f} segundos.")


if __name__ == "__main__":
    main()
