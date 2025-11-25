#!/bin/bash

# CONFIGURACIÓN DE LA RED AD HOC
PUERTO="1234"

# --- COMANDO DE RECEPCIÓN ---
# Las flags de baja latencia son CRUCIALES aquí
ffplay -fflags nobuffer -flags low_delay -framedrop -sync ext \
       -f rtp_mpegts -probesize 32 -analyzeduration 1 \
       "udp://:$PUERTO"
