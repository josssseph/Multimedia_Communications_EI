#!/bin/bash

# =======================================================
# Script: restaurar_red.sh
# Descripción: Revierte la configuración de red Ad Hoc 
#              y reactiva NetworkManager.
# =======================================================

#CONFIGURACIÓN DE LA INTERFAZ
INTERFACE="wlo1"      

# --------------------------------------------------------

# 1. VERIFICAR PERMISOS
if [ "$EUID" -ne 0 ]; then
  echo "Este script debe ejecutarse con sudo."
  echo "Uso: sudo ./restaurar_red.sh"
  exit 1
fi

echo "--------------------------------"
echo "INICIANDO RESTAURACIÓN DE LA RED"
echo "Interfaz a limpiar: $INTERFACE"

# 2. LIMPIEZA DE CONFIGURACIÓN
echo "2.1 Bajando la interfaz $INTERFACE..."
ip link set "$INTERFACE" down

echo "2.2 Limpiando direcciones IP y configuración de la interfaz..."
# Elimina cualquier dirección IP configurada manualmente en la interfaz.
ip addr flush dev "$INTERFACE"

# Limpia cualquier configuración 
iwconfig "$INTERFACE" mode auto
iwconfig "$INTERFACE" essid off
iwconfig "$INTERFACE" channel auto

# 3. RESTAURACIÓN DE NETWORKMANAGER
echo "3.1 Levantando la interfaz $INTERFACE..."
ip link set "$INTERFACE" up

echo "3.2 Reiniciando NetworkManager..."
# Usamos 'systemctl' para reactivar NetworkManager en Ubuntu 24.04
systemctl start NetworkManager

# 4. VERIFICACIÓN FINAL
echo "----------------------"
echo "RESTAURACIÓN TERMINADA"
echo "NetworkManager ha sido reiniciado."
