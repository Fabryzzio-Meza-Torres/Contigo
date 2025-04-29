import base64
import requests
from PIL import Image
from io import BytesIO
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Clave de API de Hugging Face
#HUGGINGFACE_API_KEY = "hf_abcd1234exampletoken5678"

HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

# URL del modelo en Hugging Face
API_URL = "https://api-inference.huggingface.co/models/Anwarkh1/Skin_Cancer-Image_Classification"

# Verificación de la clave
if not HUGGINGFACE_API_KEY:
    raise ValueError("Falta la variable de entorno HUGGINGFACE_API_KEY")

HEADERS = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}


def preprocess_image(image: Image.Image) -> str:
    """Convierte la imagen a base64 para enviar a la API."""
    max_size = (1024, 1024)
    image.thumbnail(max_size)
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


def analyze_image_via_api(image: Image.Image) -> dict:
    """Envía la imagen a la API de Hugging Face y devuelve el resultado procesado."""
    from io import BytesIO
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    img_bytes = buffered.getvalue()

    response = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {HUGGINGFACE_API_KEY}",
            "Content-Type": "application/octet-stream"  # Formato correcto
        },
        data=img_bytes  # Enviar bytes directamente
    )

    if response.status_code != 200:
        return {"error": f"API error: {response.status_code} - {response.text}"}
    result = response.json()
    return interpret_result(result)

"""    img_str = preprocess_image(image)
    payload = {"inputs": {"image": img_str}}

    response = requests.post(API_URL, headers=HEADERS, json=payload)

    if response.status_code != 200:
        raise RuntimeError(f"API error: {response.status_code} - {response.text}")

    result = response.json()

    return interpret_result(result)"""


def interpret_result(result) -> dict:
    """Procesa el resultado de la API para extraer la etiqueta y confianza."""
    if isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict):
        label = result[0].get("label", "unknown")
        confidence = result[0].get("score", 0.5)
    elif isinstance(result, dict):
        try:
            label, confidence = max(result.items(), key=lambda x: x[1])
        except:
            label, confidence = "unknown", 0.5
    else:
        label, confidence = "unknown", 0.5

    # Normalización de etiquetas
    label = label.lower()
    if "malig" in label or "cancer" in label:
        label = "malignant"
    elif "benig" in label or "normal" in label:
        label = "benign"

    # Normalización de confianza
    if not isinstance(confidence, (int, float)):
        confidence = 0.5
    elif confidence > 1:
        confidence /= 100

    return {"label": label, "confidence": confidence}
