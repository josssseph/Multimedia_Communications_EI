#!/usr/bin/env bash
# Asegura fallo inmediato ante variables no definidas
set -u

# Validacion de argumentos de entrada
if [ $# -lt 2 ]; then
    echo "Error: Faltan argumentos."
    echo "Uso: $0 <MI_IP> <IP_PEER>"
    exit 1
fi

MI_IP="$1"
IP_PEER="$2"

VIDEO_DEVICE="/dev/video0"
AUDIO_DEVICE="hw:1,0" 

PORT_VIDEO=5000   
PORT_AUDIO=5002   
HTTP_PORT=8000    
SDP_LOCAL="stream-${MI_IP}.sdp"
SDP_PEER="stream-${IP_PEER}.sdp"
LOGFILE="peer_${MI_IP}.log"

PY_PID=""
FFMPEG_PID=""
FFPLAY_PID=""

# Funcion de limpieza cuando termine la ejecucion
cleanup() {
    echo ""
    echo "Limpiando procesos..." | tee -a "$LOGFILE"
    [ -n "$FFPLAY_PID" ] && kill "$FFPLAY_PID" 2>/dev/null || true
    [ -n "$FFMPEG_PID" ] && kill "$FFMPEG_PID" 2>/dev/null || true
    [ -n "$PY_PID" ] && kill "$PY_PID" 2>/dev/null || true
    rm -f "$SDP_LOCAL" "$SDP_PEER"
    echo "Fin." | tee -a "$LOGFILE"
}
trap cleanup EXIT INT TERM

echo "****************************************************************"
echo "INICIO ($MI_IP <--> $IP_PEER)" | tee "$LOGFILE"
echo "Log: $LOGFILE"

# 1. TRANSMISION 

echo "Iniciando FFMPEG..."
ffmpeg \
  -f v4l2 -thread_queue_size 64 -video_size cif -i "$VIDEO_DEVICE" \
  -f alsa -thread_queue_size 64 -i "$AUDIO_DEVICE" \
  -use_wallclock_as_timestamps 1 \
  \
  -map 0:v \
  -c:v libx264 -b:v 200k\
  -preset ultrafast -tune zerolatency -pix_fmt yuv420p \
  -f rtp "rtp://${IP_PEER}:${PORT_VIDEO}" \
  \
  -map 1:a \
  -c:a aac -b:a 64k -ac 1 \
  -f rtp "rtp://${IP_PEER}:${PORT_AUDIO}" \
  \
  -sdp_file "$SDP_LOCAL" -y \
  >> "$LOGFILE" 2>&1 &

FFMPEG_PID=$!
sleep 2

# Verificar si FFMPEG murio inmediatamente
if ! kill -0 $FFMPEG_PID 2>/dev/null; then
    echo "FFMPEG fallo al iniciar. Revisa el log:"
    cat "$LOGFILE"
    exit 1
fi

# 2. SERVIDOR SDP

python3 -m http.server "$HTTP_PORT" --directory . > /dev/null 2>&1 &
PY_PID=$!
echo "Servidor SDP en puerto $HTTP_PORT"

# 3. RECEPCION SDP

echo "Esperando conexion de $IP_PEER..."
TRIES=0
MAX_TRIES=15
FOUND=0

until [ $TRIES -ge $MAX_TRIES ]; do
    if wget -q -O "$SDP_PEER" "http://${IP_PEER}:${HTTP_PORT}/${SDP_PEER}"; then
        FOUND=1
        break
    fi
    TRIES=$((TRIES+1))
    echo -ne "Intento $TRIES/$MAX_TRIES...\r"
    sleep 1
done
echo ""

if [ $FOUND -eq 0 ]; then
    echo "Tiempo agotado esperando a $IP_PEER" | tee -a "$LOGFILE"
    exit 1
fi

echo "Conexion establecida." | tee -a "$LOGFILE"


# 4. REPRODUCCION

if [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; then
    ffplay \
      -window_title "Recibiendo video de: ${IP_PEER}" \
      -protocol_whitelist file,http,udp,rtp \
      -flags low_delay \
      -probesize 100k \
      -sync ext \
      -i "$SDP_PEER" >> "$LOGFILE" 2>&1 &
    FFPLAY_PID=$!
else
    echo "Sin entorno grafico. FFPLAY omitido." | tee -a "$LOGFILE"
fi

echo "Presiona [ENTER] para salir."
read -r
