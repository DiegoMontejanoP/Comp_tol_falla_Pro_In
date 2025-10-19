import os
import asyncio
import aiohttp
from datetime import datetime
from typing import Any, Dict, List
import re
import json
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()


class MCPServer:
    def __init__(self, name: str = "email-classifier"):
        self.name = name
        self.tools = {}
        self.register_tools()

    def register_tool(self, name: str, function: callable):
        """Registra una herramienta en el servidor MCP"""
        self.tools[name] = function

    def register_tools(self):
        """Registra todas las herramientas disponibles"""
        self.register_tool("classify_email", self.classify_email)
        self.register_tool("suggest_response", self.suggest_response)
        self.register_tool("extract_urgency", self.extract_urgency)
        self.register_tool("analyze_sentiment", self.analyze_sentiment)

    async def classify_email(self, email_content: str, sender: str, subject: str) -> Dict[str, Any]:
        """Clasifica un correo electrónico en categorías específicas"""
        print(f"🔍 Clasificando email: {subject}")

        # Análisis básico del contenido
        content_lower = (email_content + " " + subject).lower()

        # Lógica de clasificación
        category = await self._determine_category(content_lower, sender)
        confidence = await self._calculate_confidence(content_lower, category)

        return {
            "category": category,
            "confidence": confidence,
            "analysis_time": datetime.now().isoformat(),
            "sender_domain": sender.split('@')[-1] if '@' in sender else "unknown"
        }

    async def _determine_category(self, content: str, sender: str) -> str:
        """Determina la categoría del correo"""
        urgent_indicators = ["urgent", "asap", "emergency", "crítico", "importante", "deadline", "hoy"]
        spam_indicators = ["offer", "win", "prize", "gratis", "descuento", "click here", "limited time"]
        newsletter_indicators = ["newsletter", "bulletin", "update", "digest"]
        support_indicators = ["help", "soporte", "support", "problem", "issue", "error"]

        if any(indicator in content for indicator in urgent_indicators):
            return "URGENT"
        elif any(indicator in content for indicator in spam_indicators):
            return "SPAM"
        elif any(indicator in content for indicator in newsletter_indicators):
            return "NEWSLETTER"
        elif any(indicator in content for indicator in support_indicators):
            return "SUPPORT"
        elif "newsletter" in sender.lower():
            return "NEWSLETTER"
        else:
            return "IMPORTANT"

    async def _calculate_confidence(self, content: str, category: str) -> float:
        """Calcula la confianza de la clasificación"""
        base_confidence = 0.7

        # Aumentar confianza basado en indicadores fuertes
        strong_indicators = {
            "URGENT": ["urgent", "asap", "emergency"],
            "SPAM": ["win", "prize", "free"],
            "NEWSLETTER": ["newsletter", "unsubscribe"],
            "SUPPORT": ["help", "soporte", "problem"]
        }

        for indicator in strong_indicators.get(category, []):
            if indicator in content:
                base_confidence += 0.15

        return min(base_confidence, 0.95)

    async def suggest_response(self, email_content: str, category: str, tone: str = "professional") -> Dict[str, Any]:
        """Sugiere una respuesta basada en la categoría y tono"""
        print(f"💡 Generando respuesta para categoría: {category}")

        responses = {
            "URGENT": {
                "professional": "He recibido su mensaje urgente. Lo revisaré inmediatamente y le responderé en un plazo máximo de 2 horas.",
                "friendly": "¡Gracias por el mensaje! Lo reviso ahora mismo y te respondo pronto."
            },
            "SUPPORT": {
                "professional": "Gracias por contactar a soporte. Hemos recibido su consulta y le asignaremos un ticket. Le responderemos en un plazo de 24 horas.",
                "friendly": "¡Hola! Recibimos tu consulta de soporte. Te ayudaremos lo antes posible."
            },
            "IMPORTANT": {
                "professional": "He recibido su mensaje. Lo revisaré y le daré seguimiento apropiado durante el día.",
                "friendly": "¡Gracias por tu mensaje! Lo revisaré hoy mismo y te respondo."
            },
            "NEWSLETTER": {
                "professional": "Gracias por la información. La revisaré cuando tenga disponibilidad.",
                "friendly": "¡Gracias por el newsletter! Lo leeré cuando tenga un momento."
            }
        }

        suggested_response = responses.get(category, {}).get(tone, "He recibido su mensaje. Le responderé pronto.")

        return {
            "suggested_response": suggested_response,
            "category": category,
            "tone": tone,
            "response_length": len(suggested_response)
        }

    async def extract_urgency(self, email_content: str) -> Dict[str, Any]:
        """Extrae nivel de urgencia y fechas límite"""
        print("⏰ Analizando urgencia del email")

        # Palabras clave de urgencia
        urgency_keywords = ["urgent", "asap", "emergency", "immediately", "now", "hoy", "inmediato", "crítico"]
        deadline_keywords = ["deadline", "by", "before", "hasta", "para el"]

        # Buscar fechas
        date_patterns = [
            r'\b\d{1,2}/\d{1,2}/\d{4}\b',
            r'\b\d{1,2}-\d{1,2}-\d{4}\b',
            r'\b\d{1,2} de [a-zA-Z]+ de \d{4}\b'
        ]

        dates_found = []
        for pattern in date_patterns:
            dates_found.extend(re.findall(pattern, email_content, re.IGNORECASE))

        # Calcular puntaje de urgencia
        urgency_score = 0
        content_lower = email_content.lower()

        for keyword in urgency_keywords:
            if keyword in content_lower:
                urgency_score += 1

        for keyword in deadline_keywords:
            if keyword in content_lower:
                urgency_score += 2

        return {
            "urgency_score": min(urgency_score, 10),
            "deadlines": dates_found,
            "has_urgency": urgency_score > 0,
            "urgency_level": "HIGH" if urgency_score > 5 else "MEDIUM" if urgency_score > 2 else "LOW"
        }

    async def analyze_sentiment(self, email_content: str) -> Dict[str, Any]:
        """Analiza el sentimiento del correo (básico)"""
        print("😊 Analizando sentimiento del email")

        positive_words = ["gracias", "thanks", "excelente", "great", "good", "bueno", "aprecio", "feliz"]
        negative_words = ["problema", "problem", "error", "bad", "mal", "enojado", "angry", "frustrado"]

        content_lower = email_content.lower()

        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)

        if positive_count > negative_count:
            sentiment = "POSITIVE"
        elif negative_count > positive_count:
            sentiment = "NEGATIVE"
        else:
            sentiment = "NEUTRAL"

        return {
            "sentiment": sentiment,
            "positive_indicators": positive_count,
            "negative_indicators": negative_count,
            "confidence": abs(positive_count - negative_count) / max(1, (positive_count + negative_count))
        }

    async def handle_request(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Maneja las solicitudes a las herramientas"""
        if tool_name in self.tools:
            return await self.tools[tool_name](**kwargs)
        else:
            return {"error": f"Tool {tool_name} not found"}


# Servidor FastAPI para exponer las herramientas
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Email Classifier MCP Server")
mcp_server = MCPServer()


class ToolRequest(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]


class EmailClassificationRequest(BaseModel):
    email_content: str
    sender: str
    subject: str


@app.post("/tools/{tool_name}")
async def call_tool(tool_name: str, request: Dict[str, Any]):
    """Endpoint para llamar herramientas específicas"""
    try:
        result = await mcp_server.handle_request(tool_name, **request)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/classify")
async def classify_email(request: EmailClassificationRequest):
    """Endpoint específico para clasificación de emails"""
    try:
        result = await mcp_server.classify_email(
            request.email_content,
            request.sender,
            request.subject
        )
        return {"success": True, "classification": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Endpoint de salud del servidor"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/tools")
async def list_tools():
    """Lista todas las herramientas disponibles"""
    return {"tools": list(mcp_server.tools.keys())}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("MCP_PORT", "3000"))
    print(f"🚀 Starting MCP Server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)