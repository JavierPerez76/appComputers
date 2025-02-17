import streamlit as st
from pymongo import MongoClient
import requests
import json
import re

def translate_text(text, target_language, subscription_key, endpoint):
    try:
        # Construir la URL y el cuerpo de la solicitud
        route = f"translate?api-version=3.0&to={target_language}"
        url = endpoint + route

        body = [{"Text": text}]
        headers = {
            'Ocp-Apim-Subscription-Key': subscription_key,
            'Content-Type': 'application/json'
        }

        # Realizar la solicitud POST
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()

        # Obtener el texto traducido
        response_json = response.json()
        translated_text = response_json[0]['translations'][0]['text']
        return translated_text

    except Exception as ex:
        st.error(f"Error al traducir: {ex}")
        return text

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

def main():
    try:
        # Cargar claves de la aplicación desde Streamlit Secrets
        translation_endpoint = st.secrets['azure_endpoint']
        translation_key = st.secrets['azure_key']
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
        target_language = st.selectbox("Selecciona un idioma para traducir:", ["es", "en", "fr", "de"])

        if user_input:
            # Traducir el texto del usuario antes de realizar la búsqueda
            translated_input = translate_text(user_input, target_language, translation_key, translation_endpoint)
            st.write(f"Texto traducido: {translated_input}")

            # Crear cliente para el modelo de Azure Language
            language_client = ConversationAnalysisClient(
                translation_endpoint, AzureKeyCredential(translation_key)
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
                                "language": target_language,
                                "text": translated_input
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
            color = None

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
                elif entity["category"] == "Color":
                    color = str(entity["text"]).lower()

            query = {}
            if pulgadas:
                query["entities.Pulgadas"] = pulgadas
            if marca:
                query["entities.Marca"] = marca
            if ram:
                query["entities.RAM"] = ram
            if color:
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
                    st.subheader(modelo)

                    st.write("### Propiedades del Ordenador:")
                    detalles = []
                    for key in ["Marca", "Codigo", "Precio", "Almacenamiento", "RAM", "Pulgadas", "Procesador", "Color", "Grafica", "Garantia"]:
                        valor = doc['entities'].get(key, 'N/A')
                        if valor != 'N/A':
                            detalles.append(f"- {key}: {valor}")

                    st.write("\n".join(detalles))

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
