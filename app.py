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

# Función para consultar la base de datos y obtener información de los ordenadores
def get_computer_info(query_params):
    # Realizar la consulta en MongoDB con los parámetros de la consulta
    computer_info = collection.find(query_params)
    if computer_info:
        return computer_info
    else:
        return "No se encontró información relacionada con la consulta."

# Función para analizar la consulta del usuario con Azure Language Understanding
def analyze_intent_and_entities(user_query):
    result = azure_client.analyze_conversation(
        task={
            "kind": "Conversation",
            "analysisInput": {
                "conversationItem": {
                    "participantId": "1",
                    "id": "1",
                    "modality": "text",
                    "language": "es",
                    "text": user_query
                },
                "isLoggingEnabled": False
            },
            "parameters": {
                "projectName": "tu_proyecto_azure",
                "deploymentName": "producción",  # Ajusta el nombre de tu despliegue
                "verbose": True
            }
        }
    )
    return result["result"]["prediction"]

# Interfaz de Streamlit
st.title("Consulta de Ordenadores")

# Input del usuario
user_query = st.text_input("¿Qué quieres saber sobre los ordenadores?", "")

if user_query:
    # Analizar la consulta del usuario para obtener intenciones y entidades
    prediction = analyze_intent_and_entities(user_query)
    top_intent = prediction["topIntent"]
    entities = prediction["entities"]

    st.subheader(f"Intención Detectada: {top_intent}")

    # Mostrar las entidades
    if entities:
        st.subheader("Entidades Reconocidas:")
        st.write(entities)
    
    # Crear un diccionario para la consulta
    query_params = {}

    # Analizar las entidades para crear la consulta
    for entity in entities:
        if entity["category"] == "RAM":
            query_params["ram"] = entity["text"]
        elif entity["category"] == "precio":
            query_params["precio"] = {"$lte": float(entity["text"].replace("€", "").strip())}
        elif entity["category"] == "marca":
            query_params["marca"] = {"$regex": entity["text"], "$options": "i"}
    
    # Mostrar la consulta que se está realizando
    st.subheader(f"Consulta generada a MongoDB: {query_params}")

    # Consultar la base de datos para obtener información del ordenador basado en la intención
    if top_intent == "comprar":  # Si la intención es comprar
        computer_info = get_computer_info(query_params)
        st.write(computer_info)
    else:
        st.write("Por favor, formula una consulta válida relacionada con la compra de un ordenador.")
