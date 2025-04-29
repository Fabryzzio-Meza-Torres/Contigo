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
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max

# Asegurarse de que la carpeta de uploads exista
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


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
    if "skin-image" not in request.files:
        return jsonify({"error": "No se ha seleccionado ningún archivo"}), 400

    file = request.files["skin-image"]

    if file.filename == "":
        return jsonify({"error": "No se ha seleccionado ningún archivo"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Formato de archivo no permitido"}), 400

    try:
        # Abrir imagen
        img = Image.open(file)

        # Redimensionar si es necesario
        max_size = (1024, 1024)
        img.thumbnail(max_size)

        # Llamar a la función de análisis que vive en api.py
        prediction = analyze_image_via_api(img)

        # Si hubo un error, devolverlo
        if "error" in prediction:
            return jsonify(prediction), 500

        return jsonify(prediction)

    except Exception as e:
        app.logger.error(f"Error en /analyze: {str(e)}")  # Log detallado
        # También imprime el error en consola
        print("ERROR EN /analyze:", str(e))
        return jsonify({
            "error": "Error al procesar la imagen",
            "details": str(e)  # Enviar detalles al frontend
        }), 500




if __name__ == "__main__":
    app.run(debug=True)
