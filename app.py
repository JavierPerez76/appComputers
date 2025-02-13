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

            # Extraer las entidades de pulgadas, marca y RAM
            for entity in entities:
                if entity["category"] == "Pulgadas":
                    pulgadas = str(entity["text"]).split()[0]  # Extraer solo el número
                elif entity["category"] == "Marca":
                    marca = str(entity["text"])
                elif entity["category"] == "RAM":
                    # Extraer solo el número de RAM, ignorando "GB de RAM" o similares
                    ram_match = re.search(r'\d+', str(entity["text"]))
                    if ram_match:
                        ram = ram_match.group(0)  # Obtener solo el número

            # Mostrar en Streamlit las entidades detectadas
            st.write(f"🔍 Entidades detectadas por Azure: {entities}")

            # Construir la consulta para MongoDB
            query = {}

            # Si se detectan pulgadas, modificamos la consulta
            if pulgadas:
                query["entities.Pulgadas"] = pulgadas  # Ajusta la clave según la estructura real

            # Si se detecta marca, filtrar también por marca
            if marca:
                query["entities.Marca"] = marca  # Ajusta la clave según la estructura real

            # Si se detecta RAM, agregar filtro por RAM (solo el número)
            if ram:
                query["entities.RAM"] = ram  # Usamos la clave 'entities.RAM' para que coincida con la base de datos

            # Mostrar la consulta generada para depuración
            st.write(f"📝 Consulta generada para MongoDB: {query}")

            # Consultar en MongoDB
            results = list(collection.find(query))

            # Generar un texto para mostrar los resultados
            if results:
                text_results = "Ordenadores encontrados:\n\n"
                for doc in results:
                    # Crear un texto con la información relevante de cada ordenador
                    text_results += f"**Marca**: {doc['entities'].get('Marca', 'N/A')}\n"
                    text_results += f"**Modelo**: {doc['entities'].get('Modelo', 'N/A')}\n"
                    text_results += f"**Código**: {doc['entities'].get('Codigo', 'N/A')}\n"
                    text_results += f"**Precio**: {doc['entities'].get('Precio', 'N/A')}\n"
                    text_results += f"**Almacenamiento**: {doc['entities'].get('Almacenamiento', 'N/A')} GB\n"
                    text_results += f"**RAM**: {doc['entities'].get('RAM', 'N/A')} GB\n"
                    text_results += f"**Pantalla**: {doc['entities'].get('Pulgadas', 'N/A')} pulgadas\n"
                    text_results += f"**Procesador**: {doc['entities'].get('Procesador', 'N/A')}\n"
                    text_results += f"**Color**: {doc['entities'].get('Color', 'N/A')}\n"
                    text_results += f"**Gráfica**: {doc['entities'].get('Grafica', 'N/A')}\n"
                    text_results += f"**Garantía**: {doc['entities'].get('Garantia', 'N/A')}\n"
                    text_results += "\n---\n"

                # Mostrar los resultados como texto
                st.text_area("Resultados de la búsqueda:", text_results, height=300)
            else:
                st.write("No se encontraron ordenadores que coincidan con tu búsqueda.")

    except Exception as ex:
        st.error(f"Error: {ex}")

if __name__ == "__main__":
    main()
