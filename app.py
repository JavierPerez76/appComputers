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

            # Extraer pulgadas
            pulgadas = None
            for entity in entities:
                if entity["category"] == "Pulgadas":
                    pulgadas = str(entity["text"])

            if pulgadas:
                # Eliminar "pulgadas" del valor de la entidad
                pulgadas_num = int(pulgadas.split()[0])  # Asumimos que siempre se da el número antes de "pulgadas"
                
                # Mostrar las entidades detectadas para depuración
                st.write(f"🔍 Entidades detectadas por Azure: {entities}")

                # Construir la consulta para MongoDB
                query = {}
                for key in collection.find():
                    # Consultar cada archivo por el valor de pulgadas
                    if 'Pulgadas' in collection[key] and collection[key]['Pulgadas'] == pulgadas_num:
                        query[key] = collection[key]

                # Mostrar la consulta generada para depuración
                st.write(f"📝 Consulta generada para MongoDB: {query}")

                # Mostrar los resultados de la consulta
                if query:
                    st.write("Ordenadores encontrados:")
                    for key, doc in query.items():
                        st.json(doc)
                else:
                    st.write("No se encontraron ordenadores que coincidan con tu búsqueda.")
            else:
                st.write("No se detectó la entidad 'Pulgadas' en la entrada.")

    except Exception as ex:
        st.error(f"Error: {ex}")

if __name__ == "__main__":
    main()
