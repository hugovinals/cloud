import os
import pickle
import numpy as np
from deepface import DeepFace
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import BlobServiceClient

# Configuración de Azure
VAULT_URL = "https://facialkeys.vault.azure.net/"
SECRET_NAME = "storage-facial"
CONTAINER_NAME = "imagenes"

# Carga de claves y clientes
credential = DefaultAzureCredential()
client = SecretClient(vault_url=VAULT_URL, credential=credential)
AZURE_CONNECTION_STRING = client.get_secret(SECRET_NAME).value
blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(CONTAINER_NAME)

# DeepFace model
MODEL_NAME = "Facenet"
DATABASE_PATH = "embeddings.pkl"

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
    usuarios.append({"nombre": nombre, "embedding": embedding})
    guardar_usuarios(usuarios)

def comparar_con_base(embedding_nuevo, umbral=0.7):
    usuarios = cargar_usuarios()
    for usuario in usuarios:
        distancia = np.linalg.norm(np.array(usuario["embedding"]) - embedding_nuevo)
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

def eliminar_imagen_blob(nombre):
    try:
        blob_name = f"{nombre}.jpg"
        container_client.delete_blob(blob_name)
    except Exception as e:
        print(f"Error eliminando imagen de Azure Blob: {e}")
