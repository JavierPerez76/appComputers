import streamlit as st
from pymongo import MongoClient
import fitz  # PyMuPDF
from azure.core.credentials import AzureKeyCredential
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

def extract_pdf_text(pdf_file):
    # Extrae texto de un PDF usando PyMuPDF
    doc = fitz.open(pdf_file)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

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

        # Subir un archivo PDF
        uploaded_pdf = st.file_uploader("Sube un archivo PDF con las características del ordenador", type=["pdf"])

        if uploaded_pdf:
            # Extraer texto del PDF
            pdf_text = extract_pdf_text(uploaded_pdf)
            st.write("Texto extraído del PDF:")
            st.write(pdf_text)

            # Procesar el texto para obtener las características
            # Aquí agregas el código para extraer las características de las entidades
            # Similar a lo que ya tienes con el análisis de lenguaje

            # Ejemplo: si el texto contiene características específicas
            marca = "Ejemplo Marca"
            ram = "16GB"
            almacenamiento = "512GB"
            color = "Negro"

            # Aquí puedes guardar la información extraída en MongoDB
            collection.insert_one({
                "marca": marca,
                "ram": ram,
                "almacenamiento": almacenamiento,
                "color": color
            })

            st.write("El ordenador se ha añadido correctamente a la base de datos.")

            # Realizar una búsqueda para encontrar un ordenador con esas características
            query = {
                "marca": marca,
                "ram": ram,
                "almacenamiento": parse_storage(almacenamiento)
            }

            results = list(collection.find(query))

            if results:
                st.write("Ordenadores encontrados:")
                for doc in results:
                    st.write(f"Marca: {doc['marca']}, RAM: {doc['ram']}, Almacenamiento: {doc['almacenamiento']}, Color: {doc['color']}")
            else:
                st.write("No se encontraron ordenadores que coincidan con las características.")

    except Exception as ex:
        st.error(f"Error: {ex}")

if __name__ == "__main__":  
    main()
