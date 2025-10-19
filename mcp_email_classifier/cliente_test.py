import asyncio
import aiohttp
import json
from datetime import datetime


class MCPClient:
    def __init__(self, base_url: str = "http://localhost:3000"):
        self.base_url = base_url

    async def test_connection(self):
        """Prueba la conexión con el servidor MCP"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        print("✅ Conexión exitosa con el servidor MCP")
                        return True
                    else:
                        print("❌ Error de conexión")
                        return False
        except Exception as e:
            print(f"❌ Error conectando al servidor: {e}")
            return False

    async def classify_test_emails(self):
        """Prueba el sistema con diferentes tipos de correos"""
        test_emails = [
            {
                "sender": "ceo@company.com",
                "subject": "URGENTE: Revisión crítica del proyecto para HOY",
                "content": "Necesito que revises este problema crítico inmediatamente. Tenemos un deadline para hoy a las 18:00. Es una emergencia."
            },
            {
                "sender": "newsletter@technews.com",
                "subject": "Weekly Tech Digest - AI Innovations",
                "content": "Descubre las últimas innovaciones en IA esta semana. Nuevos modelos, herramientas y aplicaciones prácticas."
            },
            {
                "sender": "customer@support.com",
                "subject": "Problema con la aplicación móvil",
                "content": "Hola, tengo un problema con la funcionalidad de login en la aplicación móvil. Necesito ayuda para resolverlo."
            },
            {
                "sender": "promotions@store.com",
                "subject": "¡Oferta especial! 50% de descuento",
                "content": "No te pierdas esta oferta exclusiva. Click aquí para obtener tu descuento del 50% por tiempo limitado."
            }
        ]

        print("🧪 Iniciando pruebas de clasificación...")

        for i, email in enumerate(test_emails, 1):
            print(f"\n--- Prueba {i}: {email['subject']} ---")

            # Clasificar email
            classification = await self.classify_email(
                email["content"],
                email["sender"],
                email["subject"]
            )
            print(f"📧 Clasificación: {classification.get('category', 'UNKNOWN')}")
            print(f"🎯 Confianza: {classification.get('confidence', 0):.2f}")

            # Analizar urgencia
            urgency = await self.extract_urgency(email["content"])
            print(f"⏰ Nivel de urgencia: {urgency.get('urgency_level', 'UNKNOWN')}")
            print(f"📅 Fechas encontradas: {urgency.get('deadlines', [])}")

            # Sugerir respuesta
            response = await self.suggest_response(
                email["content"],
                classification.get('category', 'IMPORTANT')
            )
            print(f"💬 Respuesta sugerida: {response.get('suggested_response', '')}")

    async def classify_email(self, email_content: str, sender: str, subject: str):
        """Clasifica un email"""
        async with aiohttp.ClientSession() as session:
            payload = {
                "email_content": email_content,
                "sender": sender,
                "subject": subject
            }
            async with session.post(f"{self.base_url}/classify", json=payload) as response:
                return await response.json()

    async def suggest_response(self, email_content: str, category: str):
        """Obtiene respuesta sugerida"""
        async with aiohttp.ClientSession() as session:
            payload = {
                "email_content": email_content,
                "category": category
            }
            async with session.post(f"{self.base_url}/tools/suggest_response", json=payload) as response:
                return await response.json()

    async def extract_urgency(self, email_content: str):
        """Extrae urgencia"""
        async with aiohttp.ClientSession() as session:
            payload = {
                "email_content": email_content
            }
            async with session.post(f"{self.base_url}/tools/extract_urgency", json=payload) as response:
                return await response.json()


async def main():
    client = MCPClient()

    # Probar conexión
    if await client.test_connection():
        # Probar clasificación
        await client.classify_test_emails()
    else:
        print("❌ No se pudo conectar al servidor MCP")


if __name__ == "__main__":
    asyncio.run(main())