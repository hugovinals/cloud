import pyodbc
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

KEY_VAULT_URL = "https://facialkeys.vault.azure.net/"
SQL_SECRET_NAME = "basedatos"  # Nombre del secreto con tu cadena de conexión

def get_connection_string():
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=KEY_VAULT_URL, credential=credential)
    secret = client.get_secret(SQL_SECRET_NAME)
    return secret.value

def get_connection():
    conn_str = get_connection_string()
    return pyodbc.connect(conn_str)

def get_usuarios():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT nombre FROM usuarios")
    result = [row[0] for row in cursor.fetchall()]
    conn.close()
    return result

def add_usuario(nombre):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO usuarios (nombre) VALUES (?)", (nombre,))
    conn.commit()
    conn.close()

def delete_usuario(nombre):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios WHERE nombre = ?", (nombre,))
    conn.commit()
    conn.close()
