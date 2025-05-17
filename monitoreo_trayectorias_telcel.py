#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de monitoreo de degradación de servicio telcel.
Realiza pruebas de conectividad vía ping y detecta eventos de degradación.

Autor: Gerencia de Soluciones Operativas
Fecha: 2025-05-16
"""

__author__    = 'Gerencia de Soluciones Operativas'
__copyright__ = 'Copyright 2024 UNINET. Todos los derechos Reservados'
__version__   = '1.8.0.R1'
__email__     = 'GSOP-ESP@uninet.com.mx'
__status__    = 'desarrollo'

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
WARNING_SEVERITY = "external.warn"


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
    mensaje = (f"%ONBOX-TELCEL-4-DEGRADATION : Se detectó degradación de servicio en el equipo {hostname} con destino {ip}")
    log_warn(mensaje)


def hacer_ping(hostname, ip):
    """Ejecuta un ping y determina si hubo degradacion."""
    dev = None
    try:

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

        avg_rtt = float(rtt.strip()) / 1000

        if perdida > MAX_PAQUETES_PERDIDOS or avg_rtt > RTT_THRESHOLD:
            return False

        return True

    except Exception as e:
        return False

    finally:
        if dev:
            dev.close()


def main():
    """Proceso principal de monitoreo."""
    data = cargar_yaml()
    if not data:
        return
    
    hostname = Junos_Context.get("hostname", "default").split(".")[0]

    if hostname not in data:
        hostname = "default"

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


    guardar_yaml({hostname: {KEY_DESTINOS: destinos}})


if __name__ == "__main__":
    main()
