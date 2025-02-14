import streamlit as st
from pymongo import MongoClient
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

            for entity in entities:
                if entity["category"] == "Pulgadas":
                    pulgadas = str(entity["text"]).split()[0]
                elif entity["category"] == "Marca":
                    marca = str(entity["text"]).lower()  # Convertir a minúsculas para comparación insensible a mayúsculas
                elif entity["category"] == "RAM":
                    ram_match = re.search(r'\d+', str(entity["text"]))
                    if ram_match:
                        ram = ram_match.group(0)
                elif entity["category"] == "Almacenamiento":
                    almacenamiento = str(entity["text"]).split()[0]
                elif entity["category"] == "ComparacionAlmacenamiento":
                    comparacion_almacenamiento = str(entity["text"]).lower()

            query = {}
            if pulgadas:
                query["entities.Pulgadas"] = pulgadas
            if marca:
                query["entities.Marca"] = {"$regex": f"^{marca}$", "$options": "i"}  # Búsqueda case-insensitive
            if ram:
                query["entities.RAM"] = ram

            if almacenamiento:
                almacenamiento_int = parse_storage(almacenamiento)
                if almacenamiento_int:
                    if comparacion_almacenamiento == "más de":
                        query["entities.Almacenamiento"] = {"$gt": almacenamiento_int}
                    elif comparacion_almacenamiento == "menos de":
                        query["entities.Almacenamiento"] = {"$lt": almacenamiento_int}
                    else:
                        query["entities.Almacenamiento"] = almacenamiento_int

            # Comprobar si la consulta de marca no tiene coincidencias exactas
            if marca and collection.count_documents({"entities.Marca": {"$regex": f"^{marca}$", "$options": "i"}}) == 0:
                # Si no se encuentra la marca, devolver un mensaje y evitar la consulta
                st.write(f"No se encontraron ordenadores de la marca {marca}.")
                return

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
    
    except Exception as ex:
        st.error(f"Error: {ex}")

if __name__ == "__main__":  
    main()
