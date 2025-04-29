from flask import Flask, render_template, request, jsonify
import os
import requests
from PIL import Image
from io import BytesIO
import base64
import json
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)

# Configuración
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max

# Asegurarse de que la carpeta de uploads exista
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Clave de API de Hugging Face - Usar un valor predeterminado si no está configurado
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")


# Función para verificar extensiones permitidas
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# Ruta principal
@app.route("/")
def index():
    return render_template("index.html")


# Ruta para la página informativa
@app.route("/about")
def about():
    return render_template("about.html")


# Endpoint para procesar las imágenes
@app.route("/analyze", methods=["POST"])
def analyze_image():
    # Verificar si hay un archivo en la solicitud
    if "file" not in request.files:
        return jsonify({"error": "No se ha seleccionado ningún archivo"}), 400

    file = request.files["file"]

    # Si el usuario no selecciona un archivo
    if file.filename == "":
        return jsonify({"error": "No se ha seleccionado ningún archivo"}), 400

    # Verificar que sea un archivo permitido
    if not allowed_file(file.filename):
        return jsonify({"error": "Formato de archivo no permitido"}), 400

    try:
        # Procesar la imagen
        img = Image.open(file)

        # Redimensionar si es necesario (asegurarse de que no sea demasiado grande)
        max_size = (1024, 1024)
        img.thumbnail(max_size)

        # Convertir imagen a formato adecuado para la API
        buffered = BytesIO()
        img.save(buffered, format="JPEG")
        img_bytes = buffered.getvalue()
        img_str = base64.b64encode(img_bytes).decode("utf-8")

        # Configuración de la API de Hugging Face
        API_URL = "https://api-inference.huggingface.co/models/MUmairAB/Breast_Cancer_Detector"

        # Asegurarse de que la clave de API esté configurada
        if not HUGGINGFACE_API_KEY:
            return (
                jsonify(
                    {
                        "error": "API key no configurada. Por favor, configure HUGGINGFACE_API_KEY en .env"
                    }
                ),
                500,
            )

        headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}

        # Enviar la imagen a la API - formato corregido
        payload = {"inputs": {"image": img_str}}
        response = requests.post(API_URL, headers=headers, json=payload)

        # Registrar la respuesta para depuración
        app.logger.info(f"API Response Status: {response.status_code}")
        app.logger.info(f"API Response Headers: {response.headers}")

        # Manejar respuesta HTTP no exitosa
        if response.status_code != 200:
            app.logger.error(f"API Error: {response.text}")
            return jsonify({"error": f"Error en la API: {response.text}"}), 500

        # Intentar procesar la respuesta JSON
        try:
            result = response.json()
            app.logger.info(f"API Response JSON: {result}")
        except Exception as e:
            app.logger.error(f"Error al parsear JSON: {str(e)}")
            return jsonify({"error": f"Error al procesar la respuesta: {str(e)}"}), 500

        # Procesar la respuesta del modelo
        try:
            # Simplificamos la lógica de procesamiento
            if isinstance(result, list) and len(result) > 0:
                # Para respuestas en formato de lista
                classification = result[0]
                if isinstance(classification, dict):
                    if "label" in classification and "score" in classification:
                        # Formato [{"label": "X", "score": 0.XX}, ...]
                        prediction = {
                            "label": classification["label"],
                            "confidence": classification["score"],
                        }
                    else:
                        # Formato {label1: score1, label2: score2, ...}
                        max_label = max(classification.items(), key=lambda x: x[1])[0]
                        max_score = classification[max_label]
                        prediction = {"label": max_label, "confidence": max_score}
                else:
                    # Formato irreconocible
                    prediction = {
                        "label": "unknown",
                        "confidence": 0.5,
                        "raw": str(result),
                    }
            elif isinstance(result, dict):
                # Para respuestas en formato de diccionario
                if "label" in result and "score" in result:
                    # Formato {"label": "X", "score": 0.XX}
                    prediction = {
                        "label": result["label"],
                        "confidence": result["score"],
                    }
                elif "labels" in result and "scores" in result:
                    # Formato {"labels": ["X", "Y"], "scores": [0.XX, 0.YY]}
                    labels = result.get("labels", [])
                    scores = result.get("scores", [])

                    if labels and scores:
                        max_index = scores.index(max(scores))
                        prediction = {
                            "label": labels[max_index],
                            "confidence": scores[max_index],
                        }
                    else:
                        prediction = {
                            "label": "unknown",
                            "confidence": 0.5,
                            "raw": str(result),
                        }
                else:
                    # Buscar el valor más alto si es un diccionario de etiquetas:puntuaciones
                    try:
                        max_label = max(result.items(), key=lambda x: x[1])[0]
                        max_score = result[max_label]
                        prediction = {"label": max_label, "confidence": max_score}
                    except:
                        prediction = {
                            "label": "unknown",
                            "confidence": 0.5,
                            "raw": str(result),
                        }
            else:
                # Formato desconocido
                prediction = {"label": "unknown", "confidence": 0.5, "raw": str(result)}

            # Normalizar etiquetas
            if isinstance(prediction.get("label"), str):
                label_lower = prediction["label"].lower()
                if "malig" in label_lower or "cancer" in label_lower:
                    prediction["label"] = "malignant"
                elif "benig" in label_lower or "normal" in label_lower:
                    prediction["label"] = "benign"

            # Asegurarse de que la confianza sea un número entre 0 y 1
            if not isinstance(prediction.get("confidence"), (int, float)):
                prediction["confidence"] = 0.5
            elif prediction["confidence"] > 1:
                prediction["confidence"] = prediction["confidence"] / 100

            return jsonify(prediction)

        except Exception as e:
            app.logger.error(f"Error al procesar resultado: {str(e)}")
            return (
                jsonify(
                    {
                        "error": f"Error al procesar el resultado: {str(e)}",
                        "raw": str(result),
                    }
                ),
                500,
            )

    except Exception as e:
        app.logger.error(f"Error general: {str(e)}")
        return jsonify({"error": f"Error al procesar la imagen: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True)
