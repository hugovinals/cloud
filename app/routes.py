from flask import Blueprint, request, render_template, redirect, url_for, flash
import os
from werkzeug.utils import secure_filename
from .recognition import (
    init_db, allowed_file, extraer_embedding, agregar_usuario,
    comparar_con_base, subir_imagen_blob, eliminar_imagen_blob,
    cargar_usuarios, guardar_usuarios
)

routes = Blueprint("routes", __name__)
UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@routes.route("/")
def home():
    return render_template("home.html")

@routes.route("/registrar", methods=["GET", "POST"])
def registrar():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        file = request.files.get("imagen")

        if not nombre or not file or file.filename == "":
            flash("Nombre o imagen inválidos.")
            return redirect(url_for("routes.registrar"))

        if not allowed_file(file.filename):
            flash("Extensión no permitida.")
            return redirect(url_for("routes.registrar"))

        filename = f"{nombre}.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        if not subir_imagen_blob(filename, filepath):
            flash("Error subiendo imagen.")
            return redirect(url_for("routes.registrar"))

        embedding = extraer_embedding(filepath)
        if not embedding:
            flash("Error extrayendo embedding.")
            return redirect(url_for("routes.registrar"))

        agregar_usuario(nombre, embedding)
        flash(f"Usuario {nombre} registrado.")
        return redirect(url_for("routes.registrar"))

    return render_template("register.html")

@routes.route("/reconocer", methods=["GET", "POST"])
def reconocer():
    if request.method == "POST":
        file = request.files.get("imagen")
        if not file or file.filename == "":
            flash("Imagen inválida.")
            return redirect(url_for("routes.reconocer"))

        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        embedding = extraer_embedding(filepath)
        if not embedding:
            flash("Error extrayendo embedding.")
            return redirect(url_for("routes.reconocer"))

        usuario = comparar_con_base(embedding)
        if usuario:
            flash(f"Usuario reconocido: {usuario['nombre']}")
        else:
            flash("Usuario no reconocido.")

        return redirect(url_for("routes.reconocer"))

    return render_template("recognize.html")

@routes.route("/usuarios")
def usuarios():
    usuarios = cargar_usuarios()
    nombres = [u["nombre"] for u in usuarios]
    return render_template("usuarios.html", usuarios=nombres)

@routes.route("/usuarios/eliminar/<nombre>", methods=["POST"])
def eliminar_usuario(nombre):
    usuarios = cargar_usuarios()
    usuarios = [u for u in usuarios if u["nombre"] != nombre]
    guardar_usuarios(usuarios)
    eliminar_imagen_blob(nombre)
    flash(f"Usuario {nombre} eliminado.")
    return redirect(url_for("routes.usuarios"))
