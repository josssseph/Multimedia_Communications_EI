#!/bin/bash

# =======================================================
# Script: crear_adhoc.sh
# Descripción: Configura una red Wi-Fi Ad Hoc (IBSS)
# =======================================================

# PARÁMETROS DE CONFIGURACIÓN DE LA RED

INTERFACE="wlo1"       
ESSID="CJ_MEI"      
CHANNEL="6"             
IP_ADDRESS="10.10.10.1" 
NETMASK="255.255.255.0" 

# --------------------------------------------------------

# 1. VERIFICAR PERMISOS (Se requiere ser root para NetworkManager e iwconfig)
if [ "$EUID" -ne 0 ]; then
  echo "Este script debe ejecutarse con sudo."
  echo "Uso: sudo ./crear_adhoc.sh"
  exit 1
fi

echo "------------------------------------"
echo "INICIANDO CONFIGURACIÓN DE RED AD HOC"
echo "Interfaz seleccionada: $INTERFACE"
echo "ESSID: $ESSID"
echo "IP: $IP_ADDRESS"

# 2. PREPARACIÓN
echo "2.1 Deteniendo NetworkManager para evitar conflictos..."
# systemctl' en Ubuntu 24.04 en lugar de 'service'
systemctl stop NetworkManager

echo "2.2 Bajando la interfaz $INTERFACE..."
ip link set "$INTERFACE" down

# 3. CONFIGURACIÓN
echo "3.1 Configurando $INTERFACE en modo Ad Hoc y parámetros..."
# Configura modo Ad-Hoc, ESSID y Canal
iwconfig "$INTERFACE" mode ad-hoc essid "$ESSID" channel "$CHANNEL"

# 4. ACTIVACIÓN y ASIGNACIÓN DE IP
echo "4.1 Levantando la interfaz $INTERFACE..."
ip link set "$INTERFACE" up

# Pequeña pausa para que el driver se estabilice
sleep 1

echo "4.2 Asignando dirección IP estática ($IP_ADDRESS)..."
# Borrar cualquier IP anterior y asignar la nueva IP estática
ip addr flush dev "$INTERFACE"
ip addr add "$IP_ADDRESS/$NETMASK" dev "$INTERFACE"

# 5. VERIFICACIÓN
echo "-----------------------"
echo "CONFIGURACIÓN TERMINADA"
echo "Verifica la configuración actual de la interfaz $INTERFACE:"
iwconfig "$INTERFACE" | grep -E "Mode|ESSID|Channel"

# Mostrar el estado de la interfaz (UP)
echo "Resultado de ip a:"
ip addr show "$INTERFACE" | grep "state"
echo "---"

