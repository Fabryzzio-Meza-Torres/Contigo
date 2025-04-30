from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
from PIL import Image
from dotenv import load_dotenv
from api import analyze_image_via_api

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuración
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024

# Crear carpeta de uploads si no existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


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
    if "skin-image" not in request.files:
        return jsonify({"error": "No se ha seleccionado ningún archivo"}), 400

    file = request.files["skin-image"]

    if file.filename == "":
        return jsonify({"error": "No se ha seleccionado ningún archivo"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Formato de archivo no permitido"}), 400

    try:
        # Abrir la imagen con PIL
        img = Image.open(file)

        # Redimensionar si es muy grande
        max_size = (1024, 1024)
        img.thumbnail(max_size)

        # Enviar a la API para análisis
        prediction = analyze_image_via_api(img)

        if "error" in prediction:
            return jsonify(prediction), 500

        # Solo procesar si devuelve una etiqueta
        if "label" in prediction:
            label = prediction["label"].lower()
            confidence = prediction["confidence"]

            # Umbral de confianza para considerar un diagnóstico como válido
            CONFIDENCE_THRESHOLD = 0.6  # 60%

            # Listas de tipos benignos y malignos
            benign_types = [
                "benign keratosis-like lesions",
                "actinic keratoses",
                "vascular lesions",
                "melanocytic nevi",
                "dermatofibroma",
            ]
            malignant_types = ["basal cell carcinoma", "melanoma"]

            # Convertimos los tipos a minúsculas para facilitar la comparación
            benign_types_lower = [bt.lower() for bt in benign_types]
            malignant_types_lower = [mt.lower() for mt in malignant_types]

            # Determinar si es benigno o maligno basado en la etiqueta (Si lees esto me debes una salchi)
            is_benign = any(bt in label for bt in benign_types_lower)
            is_malignant = any(mt in label for mt in malignant_types_lower)

            # Fallback heurístico si no coincide específicamente
            if not is_benign and not is_malignant:
                is_benign = any(
                    keyword in label for keyword in ["benign", "normal", "negative"]
                )
                is_malignant = any(
                    keyword in label
                    for keyword in ["malignant", "cancer", "positive", "carcinoma"]
                )

            # Construir respuesta con mensajes
            if is_malignant and confidence >= CONFIDENCE_THRESHOLD:
                prediction["classification"] = "malignant"
                prediction["display_message"] = "Maligno"
                prediction["pre_diagnosis"] = (
                    f"{prediction['label']}: {round(confidence * 100, 2)}%"
                )
            elif is_benign or confidence < CONFIDENCE_THRESHOLD:
                # Si es benigno o la confianza es baja, clasificamos como benigno
                prediction["classification"] = "benign"
                prediction["display_message"] = (
                    f"Benigno (No Cáncer en la piel): {round(confidence * 100, 2)}%"
                )
            else:
                # Para casos indeterminados
                prediction["classification"] = "benign"
                prediction["display_message"] = (
                    f"Benigno (No Cáncer en la piel): {round(confidence * 100, 2)}%"
                )

        return jsonify(prediction)

    except Exception as e:
        app.logger.error(f"Error en /analyze: {str(e)}")
        print("ERROR EN /analyze:", str(e))
        return jsonify({"error": "Error al procesar la imagen", "details": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
