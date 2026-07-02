#!/bin/bash
# Inicia Ollama y descarga el modelo por defecto

ollama serve &
OLLAMA_PID=$!

echo "Esperando a que Ollama inicie..."
for i in $(seq 1 30); do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "Ollama listo."
        break
    fi
    sleep 1
done

echo "Descargando modelo gemma3:4b (esto puede tardar la primera vez)..."
ollama pull gemma3:4b

echo "Modelo listo. Ollama corriendo."
wait $OLLAMA_PID
