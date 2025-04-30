import requests
import os
import io
import base64
from PIL import Image


def analyze_image_via_api(image):
    """
    Envía una imagen a la API de Hugging Face para análisis de lesiones cutáneas
    y retorna los resultados del modelo de IA.

    Args:
        image: Objeto de imagen PIL

    Returns:
        dict: Resultado de la predicción con etiqueta y confianza
    """
    try:
        # Convertir imagen a formato base64
        img_format = (image.format or "").lower()
        if img_format not in {"jpeg", "jpg", "png"}:
            return {"error": f"Formato no permitido: {img_format}. Usa jpeg, jpg, png."}

        # Convertir a RGB siempre antes de guardar como JPEG
        if image.mode != "RGB":
            image = image.convert("RGB")

        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # Obtener token de Hugging Face desde variables de entorno
        api_token = os.environ.get("HUGGING_FACE_TOKEN")
        if not api_token:
            return {"error": "No se ha configurado el token de API de Hugging Face"}

        # URL del modelo en Hugging Face para detección de cáncer de piel
        # Este es un ejemplo, deberías usar un modelo entrenado específicamente para lesiones cutáneas
        api_url = "https://api-inference.huggingface.co/models/Anwarkh1/Skin_Cancer-Image_Classification"

        # Enviar solicitud a la API
        headers = {"Authorization": f"Bearer {api_token}"}
        response = requests.post(api_url, headers=headers, json={"image": img_str})

        # Verificar respuesta
        if response.status_code != 200:
            return {"error": f"Error en la API: {response.text}"}

        # Procesar resultado
        results = response.json()

        # Si hay múltiples clasificaciones, tomar la de mayor confianza
        if isinstance(results, list) and len(results) > 0:
            top_prediction = results[0]
            label = top_prediction.get("label", "Indeterminado")
            confidence = top_prediction.get("score", 0.0)

            return {"label": label, "confidence": confidence}
        else:
            return {"error": "No se obtuvieron resultados válidos de la API"}

    except Exception as e:
        return {"error": f"Error al comunicarse con la API: {str(e)}"}
