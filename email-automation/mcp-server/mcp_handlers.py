import os
import base64
import json
import logging
from typing import List, Dict, Any
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import openai

logger = logging.getLogger(__name__)


class GmailHandler:
    def __init__(self):
        self.credentials = None
        self.service = None
        self.scopes = ['https://www.googleapis.com/auth/gmail.modify']

    async def initialize(self):
        """Inicializar la conexión con Gmail API"""
        try:
            # Cargar credenciales desde variable de entorno o archivo
            creds_json = os.getenv('GMAIL_CREDENTIALS_JSON')
            if creds_json:
                creds_info = json.loads(creds_json)
                self.credentials = Credentials.from_authorized_user_info(creds_info, self.scopes)
            else:
                # Intentar cargar desde archivo
                creds_path = '/app/credentials/gmail_credentials.json'
                if os.path.exists(creds_path):
                    self.credentials = Credentials.from_authorized_user_file(creds_path, self.scopes)

            # Refrescar token si es necesario
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())

            if self.credentials:
                self.service = build('gmail', 'v1', credentials=self.credentials)
                logger.info("✅ Gmail service inicializado correctamente")
            else:
                logger.warning("⚠️ No se encontraron credenciales de Gmail")

        except Exception as e:
            logger.error(f"❌ Error inicializando Gmail: {e}")

    async def send_email(self, to: str, subject: str, body: str, cc: List[str] = None, bcc: List[str] = None) -> str:
        """Enviar email usando Gmail API"""
        try:
            message = MIMEText(body, 'html' if '<html>' in body else 'plain')
            message['to'] = to
            message['subject'] = subject

            if cc:
                message['cc'] = ', '.join(cc)
            if bcc:
                message['bcc'] = ', '.join(bcc)

            # Codificar el mensaje
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            # Enviar el email
            message_obj = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()

            logger.info(f"📤 Email enviado a {to}, Message ID: {message_obj['id']}")
            return message_obj['id']

        except HttpError as error:
            logger.error(f"❌ Error Gmail API: {error}")
            raise Exception(f"Error enviando email: {error}")
        except Exception as e:
            logger.error(f"❌ Error enviando email: {e}")
            raise

    async def get_unread_emails(self, max_results: int = 20) -> List[Dict[str, Any]]:
        """Obtener emails no leídos"""
        try:
            if not self.service:
                await self.initialize()

            results = self.service.users().messages().list(
                userId='me',
                labelIds=['INBOX', 'UNREAD'],
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            emails = []

            for msg in messages:
                message_detail = self.service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata'
                ).execute()

                headers = message_detail.get('payload', {}).get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Sin asunto')
                from_email = next((h['value'] for h in headers if h['name'] == 'From'), 'Desconocido')

                emails.append({
                    'id': msg['id'],
                    'threadId': msg.get('threadId'),
                    'subject': subject,
                    'from': from_email,
                    'snippet': message_detail.get('snippet', ''),
                    'internalDate': message_detail.get('internalDate')
                })

            return emails

        except Exception as e:
            logger.error(f"Error obteniendo emails: {e}")
            return []

    async def mark_as_read(self, message_id: str):
        """Marcar email como leído"""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            logger.info(f"✅ Email {message_id} marcado como leído")
        except Exception as e:
            logger.error(f"Error marcando como leído: {e}")

    async def health_check(self) -> bool:
        """Verificar que Gmail API esté funcionando"""
        try:
            if self.service:
                self.service.users().getProfile(userId='me').execute()
                return True
            return False
        except:
            return False


class EmailProcessor:
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.gmail_handler = GmailHandler()

    async def categorize_email(self, subject: str, snippet: str, from_email: str) -> str:
        """Categorizar email usando OpenAI"""
        try:
            prompt = f"""
            Analiza el siguiente email y categorízalo en una de estas categorías:
            - urgent: Requiere atención inmediata
            - important: Importante pero no urgente
            - newsletter: Boletines y marketing
            - social: Redes sociales y notificaciones
            - personal: Email personal
            - spam: Correo no deseado

            Email:
            De: {from_email}
            Asunto: {subject}
            Contenido: {snippet[:500]}

            Responde solo con la categoría (urgent, important, newsletter, social, personal, spam)
            """

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10
            )

            category = response.choices[0].message.content.strip().lower()
            return category

        except Exception as e:
            logger.error(f"Error categorizando email: {e}")
            return "important"

    async def generate_auto_response(self, subject: str, content: str, from_email: str) -> str:
        """Generar respuesta automática usando OpenAI"""
        try:
            prompt = f"""
            Genera una respuesta profesional y apropiada para este email.
            Mantén un tono cordial y útil.

            Email recibido:
            De: {from_email}
            Asunto: {subject}
            Contenido: {content[:1000]}

            Responde con el contenido del email de respuesta (solo el cuerpo).
            """

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error generando respuesta: {e}")
            return "Gracias por tu email. Te responderé pronto."

    async def process_single_email(self, message_id: str, thread_id: str, from_email: str, subject: str, snippet: str):
        """Procesar un email individual"""
        try:
            logger.info(f"🔄 Procesando email: {subject}")

            # Categorizar el email
            category = await self.categorize_email(subject, snippet, from_email)
            logger.info(f"📂 Email categorizado como: {category}")

            # Acciones basadas en la categoría
            if category == "urgent":
                # Generar y enviar respuesta automática para emails urgentes
                response = await self.generate_auto_response(subject, snippet, from_email)
                await self.gmail_handler.send_email(
                    to=from_email,
                    subject=f"Re: {subject}",
                    body=f"Gracias por tu email urgente. Estoy revisando tu solicitud.\n\n{response}"
                )

            elif category == "newsletter" or category == "spam":
                # Archivar newsletters y spam
                await self.gmail_handler.mark_as_read(message_id)

            # Guardar categorización en log
            logger.info(f"✅ Email {message_id} procesado como {category}")

        except Exception as e:
            logger.error(f"❌ Error procesando email {message_id}: {e}")

    async def process_emails_batch(self, label: str = "INBOX", max_emails: int = 10, action: str = "categorize"):
        """Procesar un lote de emails"""
        try:
            emails = await self.gmail_handler.get_unread_emails(max_emails)
            logger.info(f"🔄 Procesando lote de {len(emails)} emails")

            for email in emails:
                await self.process_single_email(
                    email['id'],
                    email['threadId'],
                    email['from'],
                    email['subject'],
                    email['snippet']
                )

            logger.info(f"✅ Lote de emails procesado exitosamente")

        except Exception as e:
            logger.error(f"❌ Error procesando lote de emails: {e}")