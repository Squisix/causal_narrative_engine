#!/bin/bash
# Inicia Ollama y descarga el modelo por defecto

# Detectar e inyectar certificado Zscaler opcional si existe en el root del proyecto (/app_host)
if [ -d "/app_host" ]; then
    CERT_FOUND=""
    if [ -f "/app_host/zscaler" ]; then
        CERT_FOUND="/app_host/zscaler"
    elif [ -f "/app_host/zscaler.crt" ]; then
        CERT_FOUND="/app_host/zscaler.crt"
    elif [ -f "/app_host/zscaler.pem" ]; then
        CERT_FOUND="/app_host/zscaler.pem"
    elif [ -f "/app_host/zscaler.cer" ]; then
        CERT_FOUND="/app_host/zscaler.cer"
    fi

    if [ -n "$CERT_FOUND" ]; then
        echo "Certificado local de Zscaler encontrado en $CERT_FOUND. Instalando..."
        cp "$CERT_FOUND" /usr/local/share/ca-certificates/zscaler.crt
        update-ca-certificates
        echo "Certificado instalado correctamente."
    else
        echo "No se encontró certificado opcional de Zscaler en el root."
    fi
fi

ollama serve &
OLLAMA_PID=$!

echo "Esperando a que Ollama inicie..."
for i in $(seq 1 30); do
    if ollama list > /dev/null 2>&1; then
        echo "Ollama listo."
        break
    fi
    sleep 1
done

echo "Descargando modelo gemma3:4b (esto puede tardar la primera vez)..."
ollama pull gemma3:4b

echo "Modelo listo. Ollama corriendo."
wait $OLLAMA_PID
