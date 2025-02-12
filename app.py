import streamlit as st
from pymongo import MongoClient
from azure.ai.language.conversations import ConversationAnalysisClient
from azure.core.credentials import AzureKeyCredential

# Conexión a la base de datos MongoDB utilizando los secretos de Streamlit
mongodb_connection_string = st.secrets["mongodb_connection_string"]
client = MongoClient(mongodb_connection_string)
db = client["nombre_de_tu_base_de_datos"]
collection = db["computers"]  # Colección donde están los datos de los ordenadores

# Configuración de Azure utilizando los secretos de Streamlit
azure_endpoint = st.secrets["azure_endpoint"]
azure_key = st.secrets["azure_key"]
azure_client = ConversationAnalysisClient(endpoint=azure_endpoint, credential=AzureKeyCredential(azure_key))

# Tu código de Streamlit y funciones van aquí...
st.title("Consulta de Ordenadores")
