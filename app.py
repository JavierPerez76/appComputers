import streamlit as st
from pymongo import MongoClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.language.conversations import ConversationAnalysisClient
import re

def extract_storage(user_input):
    # Expresión regular para detectar valores de almacenamiento en GB o TB
    match = re.search(r'(\d+)\s*(GB|TB)', user_input, re.IGNORECASE)
    if match:
        value = int(match.group(1))
        unit = match.group(2).upper()
        if unit == 'TB':
            return value * 1000  # Convertir TB a GB
        return value  # Ya está en GB
    return None

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
            # Extraer el valor de almacenamiento manualmente
            almacenamiento_int = extract_storage(user_input)
            comparacion_almacenamiento = "más de" if "más de" in user_input else "menos de" if "menos de" in user_input else None

            if almacenamiento_int:
                st.write(f"Almacenamiento detectado: {almacenamiento_int} GB")
                if comparacion_almacenamiento:
                    # Ajustar consulta en MongoDB según la comparación
                    if comparacion_almacenamiento == "más de":
                        query = {"entities.Almacenamiento": {"$gt": almacenamiento_int}}
                    elif comparacion_almacenamiento == "menos de":
                        query = {"entities.Almacenamiento": {"$lt": almacenamiento_int}}
                    else:
                        query = {"entities.Almacenamiento": almacenamiento_int}

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
                else:
                    st.write("No se detectó una comparación válida en el almacenamiento.")
            else:
                st.write("No se pudo interpretar el almacenamiento correctamente.")
    except Exception as ex:
        st.error(f"Error: {ex}")

if __name__ == "__main__":
    main()
