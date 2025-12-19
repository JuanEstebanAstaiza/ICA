#!/bin/bash
# Script de inicio rápido para el Sistema ICA con Docker
# Quick start script for ICA System with Docker

set -e

echo "🚀 Iniciando Sistema ICA con Docker..."
echo "=================================="
echo ""

# Verificar que Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker no está instalado"
    echo "Por favor instala Docker desde: https://docs.docker.com/get-docker/"
    exit 1
fi

# Verificar que Docker Compose está disponible
if ! docker compose version &> /dev/null; then
    echo "❌ Error: Docker Compose no está disponible"
    echo "Por favor instala Docker Compose desde: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker encontrado: $(docker --version)"
echo "✅ Docker Compose encontrado: $(docker compose version)"
echo ""

# Detener contenedores existentes si los hay
echo "🛑 Deteniendo contenedores existentes (si los hay)..."
docker compose down 2>/dev/null || true
echo ""

# Construir e iniciar servicios
echo "🏗️  Construyendo e iniciando servicios..."
echo "Esto puede tomar unos minutos la primera vez..."
docker compose up -d --build

echo ""
echo "⏳ Esperando que los servicios estén listos..."
sleep 10

# Verificar estado de servicios
echo ""
echo "📊 Estado de los servicios:"
docker compose ps

echo ""
echo "✅ ¡Sistema iniciado correctamente!"
echo ""
echo "🌐 Accede a la aplicación en:"
echo "   • API Backend: http://localhost:8000"
echo "   • Documentación API: http://localhost:8000/api/docs"
echo "   • Health Check: http://localhost:8000/health"
echo ""
echo "📝 Para ver los logs en tiempo real:"
echo "   docker compose logs -f"
echo ""
echo "🛑 Para detener el sistema:"
echo "   docker compose down"
echo ""
echo "📚 Más información en: docs/DOCKER.md"
echo ""
