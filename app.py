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
        ls_prediction_endpoint = os.getenv('LS_CONVERSATIONS_ENDPOINT')
        ls_prediction_key = os.getenv('LS_CONVERSATIONS_KEY')
        mongodb_connection_string = os.getenv('MONGODB_CONNECTION_STRING')

        # Conectar a MongoDB
        client = MongoClient(mongodb_connection_string)
        db = client["OrdenadoresDB"]
        collection = db["Especificaciones"]

        st.title("Buscador de Ordenadores")

        # Pedir entrada al usuario
        user_input = st.text_input("¿Qué tipo de ordenador buscas?", "")

        if user_input:
            # Crear un cliente para el modelo del servicio de lenguaje
            client = ConversationAnalysisClient(
                ls_prediction_endpoint, AzureKeyCredential(ls_prediction_key)
            )

            # Llamar al modelo del servicio de lenguaje para obtener la intención y entidades
            cls_project = 'OrdenadoresConversational'
            deployment_slot = 'IntentOrdenadores'

            with client:
                query = user_input
                result = client.analyze_conversation(
                    task={
                        "kind": "Conversation",
                        "analysisInput": {
                            "conversationItem": {
                                "participantId": "1",
                                "id": "1",
                                "modality": "text",
                                "language": "es",
                                "text": query
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

            # Mostrar entidades en la terminal
            print("Entidades detectadas:")
            for entity in entities:
                print(f"Categoría: {entity['category']}, Texto: {entity['text']}")

            # Extraer pulgadas y marca de las entidades
            pulgadas = None
            marca = None

            for entity in entities:
                if entity["category"] == "pulgadas":
                    pulgadas = entity["text"]
                elif entity["category"] == "marca":
                    marca = entity["text"]

            # Construir la consulta para MongoDB
            query = {}
            if pulgadas:
                query["Pulgadas"] = pulgadas
            if marca:
                query["Marca"] = marca

            # Consultar en MongoDB
            results = list(collection.find(query))

            # Mostrar resultados
            if results:
                st.write("Ordenadores encontrados:")
                for doc in results:
                    st.write(doc)
            else:
                st.write("No se encontraron ordenadores que coincidan con tu búsqueda.")

    except Exception as ex:
        st.error(f"Error: {ex}")

if __name__ == "__main__":
    main()
