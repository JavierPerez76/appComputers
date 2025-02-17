import streamlit as st
from pymongo import MongoClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.translation.text import TextTranslationClient
from azure.ai.language.conversations import ConversationAnalysisClient
import re

def parse_storage(almacenamiento):
    match = re.match(r'(\d+\.?\d*)\s*(GB|TB)', almacenamiento, re.IGNORECASE)
    if match:
        value = float(match.group(1))
        unit = match.group(2).upper()
        if unit == 'TB':
            return int(value * 1000)  # Convertir TB a GB
        elif unit == 'GB':
            return int(value)
    return None

def translate_text(text_list, target_language):
    try:
        translator_key = st.secrets["translator_key"]
        translator_endpoint = st.secrets["translator_endpoint"]
        translator_client = TextTranslationClient(endpoint=translator_endpoint, credential=AzureKeyCredential(translator_key))

        response = translator_client.translate(content=text_list, to=[target_language])
        return [item.translations[0].text for item in response]
    except Exception as ex:
        st.error(f"Error en la traducción: {ex}")
        return text_list

def main():
    try:
        # Cargar variables de entorno
        ls_prediction_endpoint = st.secrets['azure_endpoint']
        ls_prediction_key = st.secrets['azure_key']
        mongodb_connection_string = st.secrets['mongodb_connection_string']
        blob_storage_url = st.secrets['blob_storage_url']
        sas_token = st.secrets['sas_token']

        # Conectar a MongoDB
        client = MongoClient(mongodb_connection_string)
        db = client["mongodb"]
        collection = db["computer"]

        st.title("Buscador de Ordenadores")

        # Pedir entrada al usuario
        user_input = st.text_input("¿Qué tipo de ordenador buscas?", "")

        if user_input:
            # Cliente de lenguaje en Azure
            language_client = ConversationAnalysisClient(ls_prediction_endpoint, AzureKeyCredential(ls_prediction_key))

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

            # Extraer entidades
            entities = result["result"]["prediction"]["entities"]
            query = {}
            for entity in entities:
                category = entity["category"]
                value = str(entity["text"])
                if category in ["Pulgadas", "Marca", "RAM", "Color"]:
                    query[f"entities.{category}"] = value
                elif category == "Almacenamiento":
                    query["entities.Almacenamiento"] = parse_storage(value)

            # Buscar en MongoDB
            results = list(collection.find(query))

            if results:
                for doc in results:
                    modelo = doc['entities'].get("Modelo", "N/A")
                    st.subheader(modelo)

                    # Construir las características
                    caracteristicas = []
                    for key in ["Marca", "Codigo", "Precio", "Almacenamiento", "RAM", "Pulgadas", "Procesador", "Color", "Grafica", "Garantia"]:
                        valor = doc['entities'].get(key, 'N/A')
                        if valor != 'N/A':
                            caracteristicas.append(f"{key}: {valor}")

                    # Mostrar las características originales
                    caracteristicas_texto = "\n".join(caracteristicas)
                    texto_mostrado = st.text_area("Características:", caracteristicas_texto, height=200)

                    # Botones de traducción
                    col1, col2, col3, col4 = st.columns(4)
                    if col1.button("🇬🇧 Inglés", key=f"en_{doc['_id']}"):
                        traduccion = translate_text(caracteristicas, "en")
                        texto_mostrado = "\n".join(traduccion)
                    if col2.button("🇫🇷 Francés", key=f"fr_{doc['_id']}"):
                        traduccion = translate_text(caracteristicas, "fr")
                        texto_mostrado = "\n".join(traduccion)
                    if col3.button("🇨🇳 Chino", key=f"zh_{doc['_id']}"):
                        traduccion = translate_text(caracteristicas, "zh-Hans")
                        texto_mostrado = "\n".join(traduccion)
                    if col4.button("🇷🇺 Ruso", key=f"ru_{doc['_id']}"):
                        traduccion = translate_text(caracteristicas, "ru")
                        texto_mostrado = "\n".join(traduccion)

                    st.text_area("Características traducidas:", texto_mostrado, height=200)

                    # PDF del producto
                    pdf_filename = f"{doc['_id'][:-4]}.pdf"
                    pdf_url = f"{blob_storage_url}{pdf_filename}?{sas_token}"
                    st.markdown(f"[Ver PDF aquí]({pdf_url})", unsafe_allow_html=True)

                    st.write("---")
            else:
                st.write("No se encontraron ordenadores que coincidan con tu búsqueda.")

    except Exception as ex:
        st.error(f"Error: {ex}")

if __name__ == "__main__":
    main()
