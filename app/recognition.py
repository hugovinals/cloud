import os
import numpy as np
from deepface import DeepFace
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import BlobServiceClient
import psycopg2
import psycopg2.extras

# Configuración de Azure Blob Storage
VAULT_URL = "https://facialkeys.vault.azure.net/"
SECRET_NAME = "storage-facial"
CONTAINER_NAME = "imagenes"

credential = DefaultAzureCredential()
client = SecretClient(vault_url=VAULT_URL, credential=credential)
AZURE_CONNECTION_STRING = client.get_secret(SECRET_NAME).value
blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(CONTAINER_NAME)

# DeepFace model
MODEL_NAME = "Facenet"

# Configuración base de datos PostgreSQL (cambia según tu configuración)
DB_HOST = "localhost"
DB_NAME = "tu_basedatos"
DB_USER = "tu_usuario"
DB_PASSWORD = "tu_password"
DB_PORT = 5432

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )

def init_db():
    # Crear tabla si no existe
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    nombre TEXT UNIQUE NOT NULL,
                    embedding FLOAT8[]
                );
            """)
        conn.commit()

def cargar_usuarios():
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT nombre, embedding FROM usuarios;")
            rows = cur.fetchall()
            usuarios = [{"nombre": row["nombre"], "embedding": row["embedding"]} for row in rows]
    return usuarios

def agregar_usuario(nombre, embedding):
    if not isinstance(embedding, list):
        embedding = embedding.tolist()
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO usuarios (nombre, embedding) VALUES (%s, %s) ON CONFLICT (nombre) DO UPDATE SET embedding = EXCLUDED.embedding;",
                (nombre, embedding)
            )
        conn.commit()

def eliminar_usuario(nombre):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM usuarios WHERE nombre = %s;", (nombre,))
        conn.commit()

def comparar_con_base(embedding_nuevo, umbral=0.7):
    usuarios = cargar_usuarios()
    for usuario in usuarios:
        distancia = np.linalg.norm(np.array(usuario["embedding"]) - embedding_nuevo)
        if distancia < umbral:
            return usuario
    return None

def extraer_embedding(imagen_path):
    try:
        embedding = DeepFace.represent(img_path=imagen_path, model_name=MODEL_NAME, enforce_detection=True)
        return embedding[0]["embedding"]
    except Exception as e:
        print(f"Error extrayendo embedding: {e}")
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

def eliminar_imagen_blob(nombre):
    try:
        blob_name = f"{nombre}.jpg"
        container_client.delete_blob(blob_name)
    except Exception as e:
        print(f"Error eliminando imagen de Azure Blob: {e}")
