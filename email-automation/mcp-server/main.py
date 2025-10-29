import os
import json
import logging
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
import redis

from mcp_handlers import GmailHandler, EmailProcessor

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Modelos Pydantic
class EmailRequest(BaseModel):
    to: str
    subject: str
    body: str
    cc: List[str] = []
    bcc: List[str] = []


class ProcessEmailsRequest(BaseModel):
    label: str = "INBOX"
    max_emails: int = 10
    action: str = "categorize"  # categorize, respond, archive


class GmailWebhook(BaseModel):
    message_id: str
    thread_id: str
    from_email: str
    subject: str
    snippet: str


# Inicialización de la aplicación
app = FastAPI(title="MCP Email Automation Server")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cliente Redis
redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)

# Handlers
gmail_handler = GmailHandler()
email_processor = EmailProcessor()


@app.on_event("startup")
async def startup_event():
    """Inicializar conexiones al startup"""
    try:
        # Verificar conexión a Redis
        redis_client.ping()
        logger.info("✅ Conectado a Redis")

        # Inicializar Gmail API
        await gmail_handler.initialize()
        logger.info("✅ Gmail Handler inicializado")

    except Exception as e:
        logger.error(f"❌ Error en startup: {e}")


@app.get("/")
async def root():
    return {"message": "MCP Email Automation Server", "status": "running"}


@app.post("/send-email")
async def send_email(email: EmailRequest):
    """Enviar email a través de Gmail API"""
    try:
        message_id = await gmail_handler.send_email(
            to=email.to,
            subject=email.subject,
            body=email.body,
            cc=email.cc,
            bcc=email.bcc
        )

        # Guardar en cache
        redis_client.set(f"sent_email:{message_id}", json.dumps(email.dict()))

        return {
            "status": "success",
            "message_id": message_id,
            "message": "Email enviado exitosamente"
        }

    except Exception as e:
        logger.error(f"Error enviando email: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process-emails")
async def process_emails(request: ProcessEmailsRequest, background_tasks: BackgroundTasks):
    """Procesar emails en segundo plano"""
    try:
        # Ejecutar en background
        background_tasks.add_task(
            email_processor.process_emails_batch,
            request.label,
            request.max_emails,
            request.action
        )

        return {
            "status": "processing_started",
            "message": f"Procesando {request.max_emails} emails con acción: {request.action}"
        }

    except Exception as e:
        logger.error(f"Error procesando emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/emails/unread")
async def get_unread_emails(max_results: int = 20):
    """Obtener emails no leídos"""
    try:
        emails = await gmail_handler.get_unread_emails(max_results)
        return {
            "status": "success",
            "count": len(emails),
            "emails": emails
        }
    except Exception as e:
        logger.error(f"Error obteniendo emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook/gmail")
async def gmail_webhook(webhook: GmailWebhook):
    """Webhook para notificaciones de Gmail"""
    try:
        logger.info(f"📨 Webhook recibido: {webhook.message_id}")

        # Procesar el email entrante
        await email_processor.process_single_email(
            webhook.message_id,
            webhook.thread_id,
            webhook.from_email,
            webhook.subject,
            webhook.snippet
        )

        return {"status": "processed"}

    except Exception as e:
        logger.error(f"Error procesando webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Endpoint de salud"""
    try:
        # Verificar servicios
        redis_ok = redis_client.ping()
        gmail_ok = await gmail_handler.health_check()

        return {
            "status": "healthy" if all([redis_ok, gmail_ok]) else "degraded",
            "redis": "ok" if redis_ok else "error",
            "gmail_api": "ok" if gmail_ok else "error"
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )