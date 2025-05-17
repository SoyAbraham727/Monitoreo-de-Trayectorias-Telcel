# Monitoreo-de-Trayectorias-Telcel
Proyecto para monitorear el comportamiento del servicio de internet telcel.

## Descripción

El sistema de **Monitoreo Telcel - On-Box-Junos** está diseñado para realizar pruebas de conectividad entre equipos de red utilizando **ping**. Este monitoreo ayuda a verificar la estabilidad y calidad de la red en tiempo real, ejecutando pruebas periódicas y generando alertas en caso de eventos críticos, como paquetes perdidos o tiempos de respuesta altos.

## Tabla de Actividades

A continuación, se detalla el flujo de actividades y su correspondiente procesamiento:

| **Datos de entrada**        | **Actividad**            | **Detalle de la actividad**                                                         | **Datos de salida**                                                                                  |
|-----------------------------|--------------------------|--------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------|
| IP origen, IP destino       | Pruebas de conectividad  | Se realizan 20 pruebas de ping cada 5 minutos sin calidad de servicio               | Si la prueba es exitosa, 100% de los paquetes son respondidos y los tiempos promedio son menores a 100 ms. Si se detectan paquetes perdidos o tiempos mayores a 100 ms, después de 3 eventos, se envía una alarma al correlacionador con la información del equipo origen y IP destino. |


### Criterios de aceptación
   - Con una periodicidad de cinco minutos, el equipo ejecuta el script y se realiza una prueba de conectividad vía ping para cada IP de destino definido por el usuario.
   - El script podrá enviar como máximo 20 paquetes en cada prueba de ping realizada.
   - Si el script ejecuta la prueba de conectividad vía ping y el 80 % de los paquetes son respondidos, la prueba se considera exitosa, esto no genera ninguna alarma.
   - Si el script ejecuta la prueba de conectividad y los tiempos promedio son menores a 100 ms, la prueba se considera exitosa, esto no genera ninguna alarma..
   - Si el script ejecuta la prueba de conectividad por cada ip destino definida y se detectan paquetes perdidos o tiempos promedio superiores a 100 ms, se contabiliza una prueba fallida en el archivo /tmp/gsop/trayectorias_telcel.yml.
   - El script no guardará ningún historico.
   - Si el script detecta dos eventos de degradación consecutivos hacia una misma IP de destino, se genera un evento en el log de cada equipo con el siguiente formato:
Apr  9 18:05:05  <hostname> cscript[34595]: %ONBOX-TELCEL-4-DEGRADATION : Se detectó degradación de servicio hacia el destino <ip_destino> .
   - Si el script detecta dos eventos de degradación consecutivos, correlacionador deberá tomar la cadena del syslog, procesarla y notificar en su dashboard el evento.

---
