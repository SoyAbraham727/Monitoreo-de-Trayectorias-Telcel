# Monitoreo-de-Trayectorias-Telcel
Proyecto para monitorear el comportamiento del servicio de internet telcel.

## Descripción

El sistema de **Monitoreo Telcel - On-Box-Junos** está diseñado para realizar pruebas de conectividad entre equipos de red utilizando **ping**. Este monitoreo ayuda a verificar la estabilidad y calidad de la red en tiempo real, ejecutando pruebas periódicas y generando alertas en caso de eventos críticos, como paquetes perdidos o tiempos de respuesta altos.

## Tabla de Actividades

A continuación, se detalla el flujo de actividades y su correspondiente procesamiento:

| **Datos de entrada**        | **Actividad**            | **Detalle de la actividad**                                                         | **Datos de salida**                                                                                  |
|-----------------------------|--------------------------|--------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------|
| IP origen, IP destino       | Pruebas de conectividad  | Se realizan 20 pruebas de ping cada 5 minutos sin calidad de servicio               | Si la prueba es exitosa, 100% de los paquetes son respondidos y los tiempos promedio son menores a 100 ms. Si se detectan paquetes perdidos o tiempos mayores a 100 ms, después de 3 eventos, se envía una alarma al correlacionador con la información del equipo origen y IP destino. |


### Criterios de Aceptación

1. **Monitoreo de Conectividad**: 
   - Si transcurren cinco minutos, el equipo ejecuta el script y se realizan 20 pruebas de conectividad (ping) por cada IP de destino.
   - Si el script ejecuta la prueba de conectividad y el 100 % de los paquetes son respondidos, la prueba se considera exitosa.
   - Si el script ejecuta la prueba de conectividad y los tiempos promedio son menores a 100 ms, la prueba se considera exitosa.
   - Si el script ejecuta la prueba de conectividad y se detectan paquetes perdidos o tiempos promedio superiores a 100 ms, se genera un evento de degradación.
   - Si el script detecta tres eventos de degradación consecutivos en una misma IP de destino, se envía una alarma al correlacionador con la información del equipo de origen y la IP de destino.

---
