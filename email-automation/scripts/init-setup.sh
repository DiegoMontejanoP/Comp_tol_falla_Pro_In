#!/bin/bash

echo "🚀 Iniciando configuración del sistema de automatización de emails..."

# Crear directorios necesarios
mkdir -p mcp-server/credentials
mkdir -p n8n/custom_nodes

# Verificar que Docker esté instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker no está instalado. Por favor instala Docker primero."
    exit 1
fi

# Verificar que Docker Compose esté instalado
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose no está instalado. Por favor instálalo primero."
    exit 1
fi

# Configurar variables de entorno
if [ ! -f .env ]; then
    echo "📝 Creando archivo .env..."
    cat > .env << EOF
# Credenciales Gmail
GMAIL_CREDENTIALS_JSON=

# OpenAI API Key
OPENAI_API_KEY=

# n8n Configuration
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=password123

# MCP Server
MCP_SERVER_URL=http://localhost:8000
EOF
    echo "⚠️  Por favor configura las credenciales en el archivo .env"
fi

# Dar permisos de ejecución
chmod +x scripts/*.sh

echo "✅ Configuración inicial completada!"
echo ""
echo "📋 Próximos pasos:"
echo "1. Configura las credenciales de Gmail en mcp-server/credentials/"
echo "2. Actualiza el archivo .env con tus API keys"
echo "3. Ejecuta: docker-compose up -d"
echo "4. Accede a n8n en: http://localhost:5678"