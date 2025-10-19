from typing import Any, Dict
from fastapi import FastAPI
from pydantic import BaseModel
from fastmcp import FastMCP

app = FastAPI(title="Email Triage + MCP")
mcp = FastMCP.from_fastapi(app=app, name="email-triage-mcp")  # convierte/monta MCP en /mcp

class EmailIn(BaseModel):
    subject: str
    body: str
    from_address: str | None = None

# lógica simple de clasificación (puedes sustituir por llamada a LLM)
def rule_based_classify(subject: str, body: str) -> Dict[str, Any]:
    text = (subject + " " + body).lower()
    # reglas simples
    if any(k in text for k in ["win", "free", "click here", "unsubscribe", "prize"]):
        return {"label": "Spam", "reason": "palabras típicas de spam"}
    if any(k in text for k in ["error", "failed", "urgent", "asap", "help", "immediate"]):
        return {"label": "Urgente", "reason": "menciones de urgencia/errores"}
    if any(k in text for k in ["ticket", "support", "helpdesk", "support@"]):
        return {"label": "Soporte", "reason": "parece solicitud de soporte"}
    # fallback: interesante si supera x palabras o contiene attachments (extender)
    return {"label": "Interesante", "reason": "no coincide con reglas previas"}

@app.post("/classify")
async def classify(email: EmailIn):
    result = rule_based_classify(email.subject, email.body)
    return {"ok": True, "classification": result}

# además, exponemos la misma función como tool MCP para LLMs
@mcp.tool()
def classify_email(subject: str, body: str) -> dict:
    """Clasifica un email en: Urgente | Soporte | Interesante | Spam.
    Devuelve un dict: {label: str, reason: str}"""
    return rule_based_classify(subject, body)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
