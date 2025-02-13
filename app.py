import streamlit as st
from pymongo import MongoClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.language.conversations import ConversationAnalysisClient

# Configurar las credenciales
ls_prediction_endpoint = st.secrets["azure_endpoint"]
ls_prediction_key = st.secrets["azure_key"]
mongodb_connection_string = st.secrets["mongodb_connection_string"]
blob_storage_url = st.secrets["blob_storage_url"]  # URL base del Blob Storage

# Conectar a MongoDB
client = MongoClient(mongodb_connection_string)
db = client["mongodb"]
collection = db["computers"]

st.title("Buscador de Ordenadores")

# Pedir entrada al usuario
user_input = st.text_input("¿Qué tipo de ordenador buscas?", "")

if user_input:
    # Crear un cliente para el modelo del servicio de lenguaje
    language_client = ConversationAnalysisClient(
        ls_prediction_endpoint, AzureKeyCredential(ls_prediction_key)
    )

    # Llamar al modelo del servicio de lenguaje para obtener la intención y entidades
    cls_project = 'CLUordenadores'
    deployment_slot = 'modelo'

    with language_client:
        result = language_client.analyze_conversation(
            task={
                "kind": "Conversation",
                "analysisInput": {
                    "conversationItem": {
                        "participantId": "1",
                        "id": "1",
                        "modality": "text",
                        "language": "es",
                        "text": user_input
                    },
                    "isLoggingEnabled": False
                },
                "parameters": {
                    "projectName": cls_project,
                    "deploymentName": deployment_slot,
                    "verbose": True
                }
            }
        )

    top_intent = result["result"]["prediction"]["topIntent"]
    entities = result["result"]["prediction"]["entities"]

    # Extraer pulgadas y marca de las entidades
    pulgadas = None
    marca = None

    for entity in entities:
        if entity["category"] == "pulgadas":
            pulgadas = str(entity["text"])  
        elif entity["category"] == "marca":
            marca = str(entity["text"])

    # Construir la consulta para MongoDB
    query = {}
    if pulgadas:
        query["Pulgadas.text"] = pulgadas  
    if marca:
        query["Marca.text"] = marca  

    # Consultar en MongoDB
    results = list(collection.find(query))

    # Mostrar resultados en Streamlit
    if results:
        st.write("### Ordenadores encontrados:")
        for doc in results:
            modelo = doc.get("Modelo", "Desconocido")  
            pulgadas = doc.get("Pulgadas", {}).get("text", "Desconocido")
            marca = doc.get("Marca", {}).get("text", "Desconocido")

            # Nombre del PDF en Azure Blob Storage
            pdf_filename = modelo + ".pdf"  # Asumimos que el PDF tiene el mismo nombre que el modelo
            pdf_url = f"{blob_storage_url}/{pdf_filename}"

            # Mostrar la información
            st.text(f"Modelo: {modelo}")
            st.text(f"Pulgadas: {pulgadas}")
            st.text(f"Marca: {marca}")

            # Agregar enlace al PDF
            st.markdown(f"[Ver ficha técnica]({pdf_url})", unsafe_allow_html=True)
            st.write("---")  # Separador entre resultados
    else:
        st.write("No se encontraron ordenadores que coincidan con tu búsqueda.")
