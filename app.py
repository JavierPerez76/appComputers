import streamlit as st
from pymongo import MongoClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.language.conversations import ConversationAnalysisClient

def main():
    try:
        # Cargar variables de entorno desde Streamlit Secrets
        ls_prediction_endpoint = st.secrets['azure_endpoint']
        ls_prediction_key = st.secrets['azure_key']
        mongodb_connection_string = st.secrets['mongodb_connection_string']

        # Conectar a MongoDB con la connection string
        client = MongoClient(mongodb_connection_string)  
        db = client["mongodb"]
        collection = db["computers"]

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
                query["Pulgadas"] = pulgadas  
            if marca:
                query["Marca"] = marca 

            # Mostrar la consulta en la terminal para depuración
            print("Consulta generada para MongoDB:", query)

            # Consultar en MongoDB
            results = list(collection.find(query))

            # Mostrar resultados en Streamlit
            if results:
                st.write("Ordenadores encontrados:")
                for doc in results:
                    st.json(doc)  
            else:
                st.write("No se encontraron ordenadores que coincidan con tu búsqueda.")

    except Exception as ex:
        st.error(f"Error: {ex}")

if __name__ == "__main__":
    main()
