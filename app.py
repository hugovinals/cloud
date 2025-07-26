from flask import Flask, request, render_template, redirect, url_for, flash
import os
import numpy as np
from werkzeug.utils import secure_filename
from deepface import DeepFace
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import pyodbc

# --- Configuración Azure Key Vault para obtener cadenas ---
KEY_VAULT_URL = "https://facialkeys.vault.azure.net/"

credential = DefaultAzureCredential()
secret_client = SecretClient(vault_url=KEY_VAULT_URL, credential=credential)

# Obtener cadena conexión Blob Storage
blob_secret_name = "storage-facial"
blob_connection_string = secret_client.get_secret(blob_secret_name).value

# Obtener cadena conexión Azure SQL
sql_secret_name = "BD"
sql_connection_string = secret_client.get_secret(sql_secret_name).value

# --- Conexión Blob Storage ---
CONTAINER_NAME = "imagenes"
blob_service_client = BlobServiceClient.from_connection_string(blob_connection_string)
container_client = blob_service_client.get_container_client(CONTAINER_NAME)

# --- Flask ---
app = Flask(__name__)
app.secret_key = "supersecretkey"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static/uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
MODEL_NAME = "Facenet"

# --- Funciones SQL ---
def get_connection():
    return pyodbc.connect(sql_connection_string)

def cargar_usuarios():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT nombre, embedding FROM usuarios")
    usuarios = []
    for nombre, embedding_str in cursor.fetchall():
        embedding = np.array(list(map(float, embedding_str.split(','))))
        usuarios.append({"nombre": nombre, "embedding": embedding})
    conn.close()
    return usuarios

def agregar_usuario(nombre, embedding):
    conn = get_connection()
    cursor = conn.cursor()
    embedding_str = ','.join(map(str, embedding))
    cursor.execute("INSERT INTO usuarios (nombre, embedding) VALUES (?, ?)", (nombre, embedding_str))
    conn.commit()
    conn.close()

def eliminar_usuario(nombre):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios WHERE nombre = ?", (nombre,))
    conn.commit()
    conn.close()

# --- Utilidades ---
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def extraer_embedding(imagen_path):
    try:
        embedding = DeepFace.represent(img_path=imagen_path, model_name=MODEL_NAME, enforce_detection=True)
        return embedding[0]["embedding"]
    except Exception as e:
        print(f"Error extrayendo embedding: {e}")
        return None

def comparar_con_base(embedding_nuevo, umbral=4.5):
    usuarios = cargar_usuarios()
    for usuario in usuarios:
        distancia = np.linalg.norm(usuario["embedding"] - embedding_nuevo)
        print(f"Comparando con {usuario['nombre']}, distancia: {distancia}")
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

# --- Rutas ---
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

        print("Embedding nuevo (primeros 5 valores):", embedding[:5])
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
    nombres = [u["nombre"] for u in usuarios]
    return render_template("usuarios.html", usuarios=nombres)

@app.route("/usuarios/eliminar/<nombre>", methods=["POST"])
def eliminar(nombre):
    eliminar_usuario(nombre)

    try:
        blob_name = f"{nombre}.jpg"
        container_client.delete_blob(blob_name)
    except Exception as e:
        print(f"Error eliminando imagen de Azure: {e}")

    flash(f"Usuario '{nombre}' eliminado correctamente.")
    return redirect(url_for("usuarios"))

@app.route("/comparar", methods=["GET", "POST"])
def comparar():
    distancia = None
    if request.method == "POST":
        if "imagen1" not in request.files or "imagen2" not in request.files:
            flash("Faltan ambas imágenes para comparar.")
            return redirect(url_for("comparar"))

        file1 = request.files["imagen1"]
        file2 = request.files["imagen2"]

        if file1.filename == "" or not allowed_file(file1.filename) or \
           file2.filename == "" or not allowed_file(file2.filename):
            flash("Archivos inválidos.")
            return redirect(url_for("comparar"))

        path1 = os.path.join(app.config["UPLOAD_FOLDER"], secure_filename(file1.filename))
        path2 = os.path.join(app.config["UPLOAD_FOLDER"], secure_filename(file2.filename))

        file1.save(path1)
        file2.save(path2)

        emb1 = extraer_embedding(path1)
        emb2 = extraer_embedding(path2)

        if emb1 is None or emb2 is None:
            flash("No se pudieron extraer embeddings de las imágenes.")
            return redirect(url_for("comparar"))

        distancia = np.linalg.norm(np.array(emb1) - np.array(emb2))

        print(f"Distancia calculada entre embeddings: {distancia}")

    return render_template("comparar.html", distancia=distancia)

if __name__ == "__main__":
    app.run(debug=True)
