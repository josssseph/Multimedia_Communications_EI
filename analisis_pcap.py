import os
import numpy as np
import matplotlib.pyplot as plt
from scapy.all import rdpcap, IP, UDP
import datetime

# Parámetros globales
Z_VALUE = 1.96  # Valor Z para IC del 95%

def analizar_pcapng_throughput_delay(archivo_pcapng, ip_filtro="192.168.0.101", puertos=[5000, 5002]):
    """
    Analiza archivo PCAPNG y calcula throughput y delay por intervalos de tiempo.
    Retorna: throughputs, delays, timestamp_inicial
    """
    print(f"Analizando {archivo_pcapng}...")
    
    paquetes = rdpcap(archivo_pcapng)
    
    # Filtrar paquetes bidireccionales
    paquetes_filtrados = []
    for pkt in paquetes:
        if IP in pkt and UDP in pkt:
            # Considerar tanto destino como origen
            if ((pkt[IP].dst == ip_filtro or pkt[IP].src == ip_filtro) and 
                (pkt[UDP].dport in puertos or pkt[UDP].sport in puertos)):
                paquetes_filtrados.append(pkt)
    
    if not paquetes_filtrados:
        print(f"  No se encontraron paquetes para {ip_filtro} en puertos {puertos}")
        return [], [], None
    
    print(f"  Paquetes filtrados: {len(paquetes_filtrados)}")
    
    # Convertir timestamps
    for pkt in paquetes_filtrados:
        pkt.time = float(pkt.time)
    
    timestamp_inicial = paquetes_filtrados[0].time
    throughputs = []
    delays = []
    
    intervalo = 0.01  # Cada cuanto se los paquetes (Periodo de muestreo)
    tiempo_actual = timestamp_inicial
    fin_tiempo = paquetes_filtrados[-1].time
    
    while tiempo_actual <= fin_tiempo:
        paquetes_intervalo = [p for p in paquetes_filtrados 
                             if tiempo_actual <= p.time < tiempo_actual + intervalo]
        
        if paquetes_intervalo:
            # THROUGHPUT: tasa real en bits/segundo
            bytes_totales = sum(len(p) for p in paquetes_intervalo)
            throughput_bps = (bytes_totales * 8) / intervalo  # ¡DIVIDIR por intervalo!
            throughput_mbps = throughput_bps / 1_000_000
            
            # Jitter entre paquetes consecutivos
            if len(paquetes_intervalo) > 1:
                # Calcular jitter como diferencia entre delays inter-paquete
                delays_inter_paquete = []
                for i in range(1, len(paquetes_intervalo)):
                    time_diff = paquetes_intervalo[i].time - paquetes_intervalo[i-1].time
                    delays_inter_paquete.append(time_diff * 1000)  # ms
                
                delay_promedio = np.mean(delays_inter_paquete) if delays_inter_paquete else 0
            else:
                delay_promedio = 0
            
            throughputs.append(throughput_mbps)
            delays.append(delay_promedio)
        else:
            throughputs.append(0)
            delays.append(0)
        
        tiempo_actual += intervalo
    
    return throughputs, delays, timestamp_inicial

def procesar_archivos_pcapng(directorio="."):
    """
    Procesa todos los archivos PCAPNG en el directorio.
    Retorna diccionario con datos organizados por distancia.
    """
    archivos_pcapng = [f for f in os.listdir(directorio) if f.endswith('.pcapng')]
    datos_por_distancia = {}
    
    for archivo in archivos_pcapng:
        # Extraer número de distancia del nombre del archivo
        if "UJ_D" in archivo:
            try:
                distancia = int(archivo.split('_D')[1].split('.')[0])
                throughputs, delays, _ = analizar_pcapng_throughput_delay(archivo)
                
                if throughputs and delays:
                    datos_por_distancia[distancia] = {
                        'throughput': throughputs,
                        'delay': delays
                    }
                    print(f"Distancia D{distancia}: {len(throughputs)} intervalos procesados")
            except (ValueError, IndexError) as e:
                print(f"Error procesando {archivo}: {e}")
                continue
    
    return datos_por_distancia

def calcular_estadisticas(datos_por_distancia):
    """
    Calcula estadísticas de throughput y delay para cada distancia.
    """
    resultados_throughput = {}
    resultados_delay = {}
    
    print("\n--- Cálculo de Estadísticas ---")
    
    for distancia, datos in datos_por_distancia.items():
        # Estadísticas de throughput - convertir explícitamente a numpy array de floats
        throughput_array = np.array(datos['throughput'], dtype=float)
        throughput_array = throughput_array[throughput_array > 0]  # Filtrar ceros
        
        if len(throughput_array) > 0:
            media_th = np.mean(throughput_array)
            desv_th = np.std(throughput_array, ddof=1)
            
            resultados_throughput[distancia] = {
                'Media': media_th,
                'Desviacion_Estandar': desv_th,
                'N': len(throughput_array),
                'Min': np.min(throughput_array),
                'Max': np.max(throughput_array)
            }
            
            print(f"Distancia D{distancia} - Throughput: {media_th:.4f} Mbps, σ: {desv_th:.4f}")
        else:
            print(f"Distancia D{distancia} - Throughput: Sin datos válidos")
        
        # Estadísticas de delay - convertir explícitamente a numpy array de floats
        delay_array = np.array(datos['delay'], dtype=float)
        delay_array = delay_array[delay_array > 0]  # Filtrar ceros
        
        if len(delay_array) > 0:
            media_delay = np.mean(delay_array)
            desv_delay = np.std(delay_array, ddof=1)
            
            resultados_delay[distancia] = {
                'Media': media_delay,
                'Desviacion_Estandar': desv_delay,
                'N': len(delay_array),
                'Min': np.min(delay_array),
                'Max': np.max(delay_array)
            }
            
            print(f"Distancia D{distancia} - Jitter: {media_delay:.4f} ms, σ: {desv_delay:.4f}")
        else:
            print(f"Distancia D{distancia} - Delay: Sin datos válidos")
    
    return resultados_throughput, resultados_delay

def calcular_intervalos_confianza(resultados, z_valor):
    """
    Calcula intervalos de confianza del 95% para los resultados.
    """
    print(f"\n--- Intervalos de Confianza (95%, Z={z_valor}) ---")
    
    for key, stats in resultados.items():
        if stats['N'] > 0:
            sem = stats['Desviacion_Estandar'] / np.sqrt(stats['N'])
            margen_error = z_valor * sem
            ic_bajo = stats['Media'] - margen_error
            ic_alto = stats['Media'] + margen_error
            
            stats['SEM'] = sem
            stats['Margen_Error'] = margen_error
            stats['IC_95'] = (ic_bajo, ic_alto)
            
            print(f"Distancia D{key}: ME: ±{margen_error:.4f}, IC: ({ic_bajo:.4f}, {ic_alto:.4f})")
        else:
            print(f"Distancia D{key}: Sin datos suficientes para IC")
    
    return resultados

def generar_graficas(resultados_throughput, resultados_delay, z_valor):
    """
    Genera gráficas de throughput y delay con intervalos de confianza.
    """
    # Filtrar distancias que tienen datos
    distancias_th = [d for d in resultados_throughput.keys() if resultados_throughput[d]['N'] > 0]
    distancias_delay = [d for d in resultados_delay.keys() if resultados_delay[d]['N'] > 0]
    
    if not distancias_th and not distancias_delay:
        print("No hay datos suficientes para generar gráficas")
        return
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Gráfica de Throughput
    if distancias_th:
        distancias_th_sorted = sorted(distancias_th)
        medias_th = [resultados_throughput[d]['Media'] for d in distancias_th_sorted]
        errores_th = [resultados_throughput[d]['Margen_Error'] for d in distancias_th_sorted]
        
        barras_th = ax1.bar(
            [f'D{d}' for d in distancias_th_sorted],
            medias_th,
            yerr=errores_th,
            capsize=8,
            color='#2196F3',
            ecolor='#FF5722',
            width=0.6
        )
        
        # Añadir etiquetas de valores
        for d, bar in zip(distancias_th_sorted, barras_th):
            y = bar.get_height()
            ic_bajo, ic_alto = resultados_throughput[d]['IC_95']
            texto = f"{y:.2f} Mbps\n[{ic_bajo:.2f}, {ic_alto:.2f}]"
            ax1.text(
                bar.get_x() + bar.get_width()/2,
                y + 0.01,
                texto,
                ha='center', va='bottom',
                fontsize=9, color='black'
            )
        
        ax1.set_title('Throughput Promedio por Distancia', fontsize=14)
        ax1.set_xlabel('Distancia', fontsize=12)
        ax1.set_ylabel('Throughput (Mbps)', fontsize=12)
        ax1.grid(axis='y', linestyle='--', alpha=0.7)
    else:
        ax1.text(0.5, 0.5, 'No hay datos de Throughput', 
                ha='center', va='center', transform=ax1.transAxes, fontsize=12)
        ax1.set_title('Throughput Promedio por Distancia', fontsize=14)
    
    # Gráfica de Delay
    if distancias_delay:
        distancias_delay_sorted = sorted(distancias_delay)
        medias_delay = [resultados_delay[d]['Media'] for d in distancias_delay_sorted]
        errores_delay = [resultados_delay[d]['Margen_Error'] for d in distancias_delay_sorted]
        
        barras_delay = ax2.bar(
            [f'D{d}' for d in distancias_delay_sorted],
            medias_delay,
            yerr=errores_delay,
            capsize=8,
            color='#4CAF50',
            ecolor='#FF5722',
            width=0.6
        )
        
        # Añadir etiquetas de valores
        for d, bar in zip(distancias_delay_sorted, barras_delay):
            y = bar.get_height()
            ic_bajo, ic_alto = resultados_delay[d]['IC_95']
            texto = f"{y:.2f} ms\n[{ic_bajo:.2f}, {ic_alto:.2f}]"
            ax2.text(
                bar.get_x() + bar.get_width()/2,
                y + 0.01,
                texto,
                ha='center', va='bottom',
                fontsize=9, color='black'
            )
        
        ax2.set_title('Jitter Promedio por Distancia', fontsize=14)
        ax2.set_xlabel('Distancia', fontsize=12)
        ax2.set_ylabel('Jitter (ms)', fontsize=12)
        ax2.grid(axis='y', linestyle='--', alpha=0.7)
    else:
        ax2.text(0.5, 0.5, 'No hay datos de Delay', 
                ha='center', va='center', transform=ax2.transAxes, fontsize=12)
        ax2.set_title('Delay Promedio por Distancia', fontsize=14)
    
    # Texto informativo
    for ax in [ax1, ax2]:
        ax.text(
            0.02, 0.02,
            f'IC: 95% (Z={z_valor})',
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment='top',
            bbox=dict(boxstyle="round,pad=0.5", fc="white", alpha=0.7)
        )
    
    plt.tight_layout()
    plt.show()

def generar_graficas_tiempo_real(datos_por_distancia):
    """
    Genera gráficas de throughput y delay en tiempo real.
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    for distancia, datos in datos_por_distancia.items():
        tiempo = range(len(datos['throughput']))
        
        # Throughput en tiempo real
        ax1.plot(tiempo, datos['throughput'], 
                label=f'D{distancia}', linewidth=2, marker='o', markersize=3)
        
        # Delay en tiempo real - solo mostrar valores positivos
        delays_positivos = [d if d > 0 else np.nan for d in datos['delay']]
        ax2.plot(tiempo, delays_positivos, 
                label=f'D{distancia}', linewidth=2, marker='s', markersize=3)
    
    ax1.set_title('Throughput en Tiempo Real por Distancia', fontsize=14)
    ax1.set_xlabel('Tiempo (segundos)', fontsize=12)
    ax1.set_ylabel('Throughput (Mbps)', fontsize=12)
    ax1.legend()
    ax1.grid(True, linestyle='--', alpha=0.7)
    
    ax2.set_title('Jitter en Tiempo Real por Distancia', fontsize=14)
    ax2.set_xlabel('Tiempo (segundos)', fontsize=12)
    ax2.set_ylabel('Jitter (ms)', fontsize=12)
    ax2.legend()
    ax2.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    # Procesar archivos PCAPNG
    datos_por_distancia = procesar_archivos_pcapng()
    
    if datos_por_distancia:
        print(f"\nSe procesaron {len(datos_por_distancia)} distancias:")
        for distancia in sorted(datos_por_distancia.keys()):
            print(f"  Distancia D{distancia}: {len(datos_por_distancia[distancia]['throughput'])} muestras")
        
        # Calcular estadísticas
        resultados_throughput, resultados_delay = calcular_estadisticas(datos_por_distancia)
        
        # Calcular intervalos de confianza
        resultados_throughput = calcular_intervalos_confianza(resultados_throughput, Z_VALUE)
        resultados_delay = calcular_intervalos_confianza(resultados_delay, Z_VALUE)
        
        # Generar gráficas
        generar_graficas(resultados_throughput, resultados_delay, Z_VALUE)
        generar_graficas_tiempo_real(datos_por_distancia)
        
    else:
        print("No se encontraron archivos PCAPNG válidos para procesar.")
