import streamlit as st
from pymongo import MongoClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.language.conversations import ConversationAnalysisClient
from azure.ai.translation.text import TextTranslationClient
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

def translate_text(text, target_language, translation_endpoint, translation_key):
    try:
        translation_client = TextTranslationClient(
            endpoint=translation_endpoint, credential=AzureKeyCredential(translation_key)
        )
        response = translation_client.translate(text=text, target_languages=[target_language])
        return response[0].translations[0].text
    except Exception as ex:
        st.error(f"Error en la traducción: {ex}")
        return text

def main():
    try:
        # Cargar variables de entorno desde Streamlit Secrets
        ls_prediction_endpoint = st.secrets['azure_endpoint']
        ls_prediction_key = st.secrets['azure_key']
        mongodb_connection_string = st.secrets['mongodb_connection_string']
        blob_storage_url = st.secrets['blob_storage_url']
        sas_token = st.secrets['sas_token']
        translation_endpoint = st.secrets['translation_endpoint']
        translation_key = st.secrets['translation_key']

        # Conectar a MongoDB con la connection string
        client = MongoClient(mongodb_connection_string)  
        db = client["mongodb"]
        collection = db["computer"]

        st.title("Buscador de Ordenadores")

        # Pedir entrada al usuario
        user_input = st.text_input("¿Qué tipo de ordenador buscas?", "")

        # Selección del idioma
        idioma = st.selectbox("Selecciona un idioma para traducir:", ["Inglés", "Francés", "Chino", "Ruso"])

        if user_input:
            # Crear un cliente para el modelo del servicio de lenguaje en Azure
            language_client = ConversationAnalysisClient(
                ls_prediction_endpoint, AzureKeyCredential(ls_prediction_key)
            )

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

            pulgadas = None
            marca = None
            ram = None
            comparacion_almacenamiento = None
            almacenamiento = None
            color = None  # Añadimos una variable para el color

            for entity in entities:
                if entity["category"] == "Pulgadas":
                    pulgadas = str(entity["text"]).split()[0]
                elif entity["category"] == "Marca":
                    marca = str(entity["text"])
                elif entity["category"] == "RAM":
                    ram_match = re.search(r'\d+', str(entity["text"]))
                    if ram_match:
                        ram = ram_match.group(0)
                elif entity["category"] == "Almacenamiento":
                    almacenamiento = str(entity["text"]).split()[0]
                elif entity["category"] == "ComparacionAlmacenamiento":
                    comparacion_almacenamiento = str(entity["text"]).lower()
                elif entity["category"] == "Color":  # Detectar color
                    color = str(entity["text"]).lower()

            query = {}
            if pulgadas:
                query["entities.Pulgadas"] = pulgadas
            if marca:
                query["entities.Marca"] = marca
            if ram:
                query["entities.RAM"] = ram
            if color:  # Si hay color, agregarlo a la consulta
                query["entities.Color"] = color

            if almacenamiento:
                almacenamiento_int = parse_storage(almacenamiento)
                if almacenamiento_int:
                    if comparacion_almacenamiento == "más de":
                        query["entities.Almacenamiento"] = {"$gt": almacenamiento_int}
                    elif comparacion_almacenamiento == "menos de":
                        query["entities.Almacenamiento"] = {"$lt": almacenamiento_int}
                    else:
                        query["entities.Almacenamiento"] = almacenamiento_int

            results = list(collection.find(query))

            if results:
                for doc in results:
                    modelo = doc['entities'].get("Modelo", "N/A")
                    st.subheader(modelo)  # Mostrar el modelo en grande

                    # Mostrar las propiedades como una lista ordenada
                    st.write("### Propiedades del Ordenador:")
                    detalles = []
                    for key in ["Marca", "Codigo", "Precio", "Almacenamiento", "RAM", "Pulgadas", "Procesador", "Color", "Grafica", "Garantia"]:
                        valor = doc['entities'].get(key, 'N/A')
                        if valor != 'N/A':
                            detalles.append(f"- {key}: {valor}")

                    # Mostrar las propiedades
                    st.write("\n".join(detalles))

                    # Mostrar el enlace para el PDF en una línea separada
                    pdf_filename = f"{doc['_id'][:-4]}.pdf"  
                    pdf_url = f"{blob_storage_url}{pdf_filename}?{sas_token}"
                    st.markdown(f"[Ver PDF aquí]({pdf_url})", unsafe_allow_html=True)

                    st.write("---")
            else:
                st.write("No se encontraron ordenadores que coincidan con tu búsqueda.")

            # Traducir todo el contenido a otro idioma
            if idioma != "Español":
                idioma_mapeado = {"Inglés": "en", "Francés": "fr", "Chino": "zh", "Ruso": "ru"}[idioma]
                translated_title = translate_text(st.session_state.title, idioma_mapeado, translation_endpoint, translation_key)
                st.title(translated_title)

                translated_results = translate_text("\n".join(detalles), idioma_mapeado, translation_endpoint, translation_key)
                st.write(translated_results)

    except Exception as ex:
        st.error(f"Error: {ex}")

if __name__ == "__main__":  
    main()
