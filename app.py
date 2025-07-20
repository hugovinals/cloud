from flask import Flask, request, render_template, redirect, url_for, flash
import os
import numpy as np
import pickle
from werkzeug.utils import secure_filename
from deepface import DeepFace
from azure.storage.blob import BlobServiceClient

# Azure Blob config
AZURE_CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=storagefacial;AccountKey=XKkpEtRLAhI/oXDbrMixR1oiLxdGIwjr4Z9cuusIZag6nr3VlmqzEkTOk3oP6GENaSwXhp0eg8rq+AStQXgavw==;EndpointSuffix=core.windows.net"
CONTAINER_NAME = "imagenes"

blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(CONTAINER_NAME)

# Flask setup
app = Flask(__name__)
app.secret_key = "supersecretkey"

UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
DATABASE_PATH = "embeddings.pkl"
MODEL_NAME = "Facenet"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Utils
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    if not os.path.exists(DATABASE_PATH):
        with open(DATABASE_PATH, "wb") as f:
            pickle.dump([], f)

def cargar_usuarios():
    if not os.path.exists(DATABASE_PATH):
        return []
    with open(DATABASE_PATH, "rb") as f:
        return pickle.load(f)

def guardar_usuarios(usuarios):
    with open(DATABASE_PATH, "wb") as f:
        pickle.dump(usuarios, f)

def extraer_embedding(imagen_path):
    try:
        embedding = DeepFace.represent(img_path=imagen_path, model_name=MODEL_NAME, enforce_detection=True)
        return embedding[0]["embedding"]
    except Exception as e:
        print(f"Error extrayendo embedding: {e}")
        return None

def agregar_usuario(nombre, embedding):
    usuarios = cargar_usuarios()
    if not isinstance(embedding, list):
        embedding = embedding.tolist()
    usuarios.append({
        "nombre": nombre,
        "embedding": embedding
    })
    guardar_usuarios(usuarios)

def comparar_con_base(embedding_nuevo, umbral=0.7):
    usuarios = cargar_usuarios()
    for usuario in usuarios:
        embedding_guardado = np.array(usuario["embedding"])
        distancia = np.linalg.norm(embedding_guardado - embedding_nuevo)
        if distancia < umbral:
            return usuario
    return None

def subir_imagen_blob(filename, filepath):
    try:
        blob_client = container_client.get_blob_client(filename)
        with open(filepath, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
        url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{CONTAINER_NAME}/{filename}"
        return url
    except Exception as e:
        print(f"Error subiendo imagen a Blob: {e}")
        return None

# Rutas
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/registrar", methods=["GET", "POST"])
def registrar():
    if request.method == "POST":
        if "imagen" not in request.files or "nombre" not in request.form:
            flash("Faltan datos para registrar.")
            return redirect(url_for("registrar"))

        nombre = request.form["nombre"].strip()
        file = request.files["imagen"]

        if file.filename == "" or not allowed_file(file.filename):
            flash("Archivo inválido.")
            return redirect(url_for("registrar"))

        filename = f"{nombre}.jpg"
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        url_imagen = subir_imagen_blob(filename, filepath)
        if url_imagen is None:
            flash("Error subiendo imagen a Blob Storage.")
            return redirect(url_for("registrar"))

        embedding = extraer_embedding(filepath)
        if embedding is None:
            flash("No se pudo extraer embedding de la imagen.")
            return redirect(url_for("registrar"))

        agregar_usuario(nombre, embedding)
        flash(f"Usuario {nombre} registrado correctamente.")
        return redirect(url_for("registrar"))

    return render_template("register.html")

@app.route("/reconocer", methods=["GET", "POST"])
def reconocer():
    if request.method == "POST":
        if "imagen" not in request.files:
            flash("No se envió ninguna imagen.")
            return redirect(url_for("reconocer"))

        file = request.files["imagen"]

        if file.filename == "" or not allowed_file(file.filename):
            flash("Archivo inválido.")
            return redirect(url_for("reconocer"))

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        embedding = extraer_embedding(filepath)
        if embedding is None:
            flash("No se pudo extraer embedding de la imagen.")
            return redirect(url_for("reconocer"))

        usuario = comparar_con_base(embedding)
        if usuario:
            flash(f"Usuario reconocido: {usuario['nombre']}")
        else:
            flash("Usuario no reconocido.")
        return redirect(url_for("reconocer"))

    return render_template("recognize.html")

@app.route("/usuarios")
def usuarios():
    usuarios = cargar_usuarios()
    # Solo enviamos los nombres, sin imágenes
    nombres = [u["nombre"] for u in usuarios]
    return render_template("usuarios.html", usuarios=nombres)

@app.route("/usuarios/eliminar/<nombre>", methods=["POST"])
def eliminar_usuario(nombre):
    usuarios = cargar_usuarios()
    usuarios = [u for u in usuarios if u["nombre"] != nombre]
    guardar_usuarios(usuarios)

    # Intentamos eliminar la imagen del blob
    try:
        blob_name = f"{nombre}.jpg"
        container_client.delete_blob(blob_name)
    except Exception as e:
        print(f"Error eliminando imagen de Azure: {e}")

    flash(f"Usuario '{nombre}' eliminado correctamente.")
    return redirect(url_for("usuarios"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
