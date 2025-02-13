import streamlit as st
from dotenv import load_dotenv
import os
from pymongo import MongoClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.language.conversations import ConversationAnalysisClient

def main():
    try:
        # Cargar variables de entorno
        load_dotenv()
        ls_prediction_endpoint = st.secrets['azure_endpoint']
        ls_prediction_key = st.secrets['azure_endpoint']
        mongodb_connection_string = st.secrets['mongodb_connection_string']

        # Conectar a MongoDB
        client = MongoClient(st.secrets["mongodb_connection_string"])
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
            cls_project = 'OrdenadoresConversational'
            deployment_slot = 'IntentOrdenadores'

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

            # Mostrar entidades detectadas en la terminal
            print("Entidades detectadas:")
            for entity in entities:
                print(f"Categoría: {entity['category']}, Texto: {entity['text']}")

            # Extraer pulgadas y marca de las entidades
            pulgadas = None
            marca = None

            for entity in entities:
                if entity["category"] == "pulgadas":
                    pulgadas = str(entity["text"])  # Asegurar que sea string
                elif entity["category"] == "marca":
                    marca = str(entity["text"])  # Asegurar que sea string

            # Construir la consulta para MongoDB
            query = {}
            if pulgadas:
                query["Pulgadas.text"] = pulgadas  
            if marca:
                query["Marca.text"] = marca 

            # Mostrar la consulta en la terminal para depuración
            print("Consulta generada para MongoDB:", query)

            # Consultar en MongoDB
            results = list(collection.find(query))

            # Mostrar resultados en Streamlit
            if results:
                st.write("Ordenadores encontrados:")
                for doc in results:
                    st.json(doc)  # Mostrar en formato JSON más legible
            else:
                st.write("No se encontraron ordenadores que coincidan con tu búsqueda.")

    except Exception as ex:
        st.error(f"Error: {ex}")

if __name__ == "__main__":
    main()
