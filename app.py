import streamlit as st
from pymongo import MongoClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.language.conversations import ConversationAnalysisClient
import re

def main():
    try:
        # Cargar variables de entorno desde Streamlit Secrets
        ls_prediction_endpoint = st.secrets['azure_endpoint']
        ls_prediction_key = st.secrets['azure_key']
        mongodb_connection_string = st.secrets['mongodb_connection_string']
        blob_storage_url = st.secrets['blob_storage_url']
        sas_token = st.secrets['sas_token']

        # Conectar a MongoDB con la connection string
        client = MongoClient(mongodb_connection_string)  
        db = client["mongodb"]
        collection = db["computer"]

        st.title("Buscador de Ordenadores")

        # Pedir entrada al usuario
        user_input = st.text_input("¿Qué tipo de ordenador buscas?", "")

        if user_input:
            # Crear un cliente para el modelo del servicio de lenguaje en Azure
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

            # Inicializar las variables para las entidades
            pulgadas = None
            marca = None
            ram = None
            almacenamiento = None
            almacenamiento_comparacion = None

            # Extraer las entidades de pulgadas, marca, RAM y almacenamiento
            for entity in entities:
                if entity["category"] == "Pulgadas":
                    pulgadas = str(entity["text"]).split()[0]  # Extraer solo el número
                elif entity["category"] == "Marca":
                    marca = str(entity["text"])
                elif entity["category"] == "RAM":
                    ram_match = re.search(r'\d+', str(entity["text"]))
                    if ram_match:
                        ram = ram_match.group(0)
                elif entity["category"] == "Almacenamiento":
                    almacenamiento_match = re.search(r'\d+', str(entity["text"]))
                    if almacenamiento_match:
                        almacenamiento = int(almacenamiento_match.group(0))
                elif entity["category"] == "ComparacionAlmacenamiento":
                    almacenamiento_comparacion = str(entity["text"]).lower()

            # Construir la consulta para MongoDB
            query = {}
            if pulgadas:
                query["entities.Pulgadas"] = pulgadas
            if marca:
                query["entities.Marca"] = marca
            if ram:
                query["entities.RAM"] = ram

            # Manejo de la comparación de almacenamiento
            if almacenamiento_comparacion:
                if "más" in almacenamiento_comparacion:
                    # Si el usuario pide más de, transformamos el valor en GB
                    if almacenamiento:
                        query["entities.Almacenamiento"] = {"$gte": almacenamiento}
                elif "menos" in almacenamiento_comparacion:
                    if almacenamiento:
                        query["entities.Almacenamiento"] = {"$lte": almacenamiento}

            # Consultar en MongoDB
            results = list(collection.find(query))

            # Generar un texto para mostrar los resultados
            if results:
                text_results = "Ordenadores encontrados:\n\n"
                for doc in results:
                    detalles = []
                    for key in ["Marca", "Modelo", "Codigo", "Precio", "Almacenamiento", "RAM", "Pulgadas", "Procesador", "Color", "Grafica", "Garantia"]:
                        valor = doc['entities'].get(key, 'N/A')
                        if valor != 'N/A':
                            detalles.append(f"**{key}**: {valor}")
                    
                    pdf_filename = f"{doc['_id'][:-4]}.pdf"  
                    pdf_url = f"{blob_storage_url}{pdf_filename}?{sas_token}"
                    
                    detalles.append(f"[Ver PDF aquí]({pdf_url})")
                    text_results += "\n\n".join(detalles) + "\n\n---\n\n"
                
                st.write(text_results)
            else:
                st.write("No se encontraron ordenadores que coincidan con tu búsqueda.")
    
    except Exception as ex:
        st.error(f"Error: {ex}")

if __name__ == "__main__":
    main()
