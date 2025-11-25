#!/bin/bash

# CONFIGURACIÓN DE LA RED AD HOC
# IP del Receptor en la red Ad Hoc
RECEPTOR_IP="10.10.10.2" 
PUERTO="1234"

# CONFIGURACIÓN DE DISPOSITIVOS
# Dispositivos de entrada usando 'ls /dev/video*' y 'arecord -l'
VIDEO_DEV="/dev/video0"
AUDIO_DEV="hw:1,0"

# COMANDO DE TRANSMISIÓN
ffmpeg -f v4l2 -i "$VIDEO_DEV" \
       -f alsa -i "$AUDIO_DEV" \
       \
       -c:v libx264 -preset veryfast -tune zerolatency -bf 0 -b:v 500k -r 20 -g 20 \
       -pix_fmt yuv420p \
       \
       -c:a aac -ac 1 -b:a 64k -ar 44100 \
       -f rtp_mpegts "udp://$RECEPTOR_IP:$PUERTO"
