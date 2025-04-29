document.addEventListener("DOMContentLoaded", function () {
  // Elementos del DOM
  const fileInput = document.getElementById("mammography-image");
  const previewContainer = document.getElementById("preview-container");
  const imagePreview = document.getElementById("image-preview");
  const removeButton = document.getElementById("remove-image");
  const uploadForm = document.getElementById("upload-form");
  const resultsPanel = document.getElementById("results-panel");
  const loader = document.querySelector(".loader");
  const resultsContent = document.querySelector(".results-content");
  const resultPercentage = document.getElementById("result-percentage");
  const resultLabel = document.getElementById("result-label");
  const resultDescription = document.getElementById("result-description");
  const newAnalysisButton = document.getElementById("new-analysis");

  // Manejar cambio en el input de archivo
  fileInput.addEventListener("change", function (e) {
    if (fileInput.files && fileInput.files[0]) {
      // Validar el archivo
      const file = fileInput.files[0];
      const validTypes = ["image/jpeg", "image/jpg", "image/png"];

      if (!validTypes.includes(file.type)) {
        alert("Por favor selecciona una imagen en formato JPG, JPEG o PNG.");
        resetFileInput();
        return;
      }

      if (file.size > 16 * 1024 * 1024) {
        // 16MB max
        alert(
          "La imagen es demasiado grande. Por favor selecciona una imagen de menos de 16MB."
        );
        resetFileInput();
        return;
      }

      // Mostrar vista previa
      const reader = new FileReader();
      reader.onload = function (e) {
        imagePreview.src = e.target.result;
        previewContainer.classList.remove("hidden");
      };
      reader.readAsDataURL(file);
    }
  });

  // Eliminar imagen seleccionada
  removeButton.addEventListener("click", function () {
    resetFileInput();
    previewContainer.classList.add("hidden");
  });

  // Enviar formulario para análisis
  uploadForm.addEventListener("submit", function (e) {
    e.preventDefault();

    if (!fileInput.files || !fileInput.files[0]) {
      alert("Por favor selecciona una imagen para analizar.");
      return;
    }

    // Mostrar panel de resultados con loader
    resultsPanel.classList.remove("hidden");
    loader.classList.remove("hidden");
    resultsContent.classList.add("hidden");

    // Crear FormData para enviar la imagen
    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    // Enviar imagen al servidor
    fetch("/analyze", {
      method: "POST",
      body: formData,
    })
      .then((response) => {
        if (!response.ok) {
          return response.json().then((err) => {
            throw new Error(err.error || "Error en la respuesta del servidor");
          });
        }
        return response.json();
      })
      .then((data) => {
        // Verificar si hay un mensaje de error en la respuesta
        if (data.error) {
          throw new Error(data.error);
        }

        // Ocultar loader y mostrar resultados
        loader.classList.add("hidden");
        resultsContent.classList.remove("hidden");

        // Procesar resultado
        displayResults(data);
      })
      .catch((error) => {
        console.error("Error:", error);
        loader.classList.add("hidden");

        // Mostrar error en la interfaz
        resultsContent.classList.remove("hidden");
        resultLabel.textContent = "Error";
        resultDescription.textContent =
          error.message ||
          "Ha ocurrido un error al procesar la imagen. Por favor intenta nuevamente.";
        resultPercentage.textContent = "!";

        // Resetear clases de estilo
        resultsContent.className = "results-content";
        resultsContent.classList.add("error");
      });
  });

  // Botón para nuevo análisis
  newAnalysisButton.addEventListener("click", function () {
    resultsPanel.classList.add("hidden");
    resetFileInput();
    previewContainer.classList.add("hidden");
  });

  // Función para resetear el input de archivo
  function resetFileInput() {
    uploadForm.reset();
    imagePreview.src = "";
  }

  // Función para mostrar los resultados
  function displayResults(data) {
    // Limpiar clases anteriores
    resultsContent.className = "results-content";

    // Manejar caso de error
    if (data.error) {
      resultLabel.textContent = "Error";
      resultDescription.textContent = data.error;
      resultsContent.classList.add("error");
      resultPercentage.textContent = "!";
      return;
    }

    // Obtener detalles del resultado
    let label = data.label || "unknown";
    let confidence = data.confidence !== undefined ? data.confidence : 0.5;

    // Asegurarse de que la confianza sea un número entre 0 y 1
    if (typeof confidence !== "number") {
      confidence = 0.5;
    } else if (confidence > 1) {
      confidence = confidence / 100;
    }

    // Formatear porcentaje de confianza
    const confidencePercent = Math.round(confidence * 100);
    resultPercentage.textContent = confidencePercent + "%";

    // Determinar clasificación y descripción
    const labelLower = label.toLowerCase();
    let className, description;

    if (
      labelLower === "benign" ||
      labelLower.includes("benign") ||
      labelLower === "normal" ||
      labelLower.includes("negative")
    ) {
      className = "benign";
      resultLabel.textContent = "Posiblemente benigno";
      description = `La imagen analizada muestra características que suelen asociarse con tejido normal o benigno. El modelo de IA tiene una confianza del ${confidencePercent}% en esta clasificación.`;
    } else if (
      labelLower === "malignant" ||
      labelLower.includes("malignant") ||
      labelLower.includes("cancer") ||
      labelLower.includes("positive")
    ) {
      className = "malignant";
      resultLabel.textContent = "Posiblemente maligno";
      description = `La imagen analizada muestra características que podrían asociarse con tejido anormal o maligno. El modelo de IA tiene una confianza del ${confidencePercent}% en esta clasificación.`;
    } else {
      className = "suspicious";
      resultLabel.textContent = "Indeterminado";
      description = `El resultado del análisis no es concluyente. El modelo de IA ha clasificado la imagen como "${label}" con una confianza del ${confidencePercent}%.`;
    }

    // Actualizar interfaz
    resultsContent.classList.add(className);
    resultDescription.textContent = description;
  }

  // Verificar si hay soporte para arrastrar y soltar
  const dropArea = document.querySelector(".file-label");

  ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
    dropArea.addEventListener(eventName, preventDefaults, false);
  });

  function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
  }

  ["dragenter", "dragover"].forEach((eventName) => {
    dropArea.addEventListener(eventName, highlight, false);
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropArea.addEventListener(eventName, unhighlight, false);
  });

  function highlight() {
    dropArea.classList.add("highlight");
  }

  function unhighlight() {
    dropArea.classList.remove("highlight");
  }

  dropArea.addEventListener("drop", handleDrop, false);

  function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;

    if (files && files.length) {
      fileInput.files = files;
      // Disparar el evento 'change' manualmente
      const event = new Event("change");
      fileInput.dispatchEvent(event);
    }
  }
});
