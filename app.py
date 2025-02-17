import streamlit as st
from pymongo import MongoClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.language.conversations import ConversationAnalysisClient
import re
import fitz  # PyMuPDF

# Función para procesar almacenamiento
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

# Función para extraer texto del PDF cargado
def extract_pdf_text(uploaded_pdf):
    doc = fitz.open(stream=uploaded_pdf.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

# Función para analizar el texto con Azure CLU
def analyze_text_with_clu(text, language_client, cls_project, deployment_slot):
    result = language_client.analyze_conversation(
        task={
            "kind": "Conversation",
            "analysisInput": {
                "conversationItem": {
                    "participantId": "1",
                    "id": "1",
                    "modality": "text",
                    "language": "es",
                    "text": text
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
    return result

# Función principal
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

        # Subir un archivo PDF
        uploaded_pdf = st.file_uploader("Sube un archivo PDF con las características del ordenador", type=["pdf"])

        if uploaded_pdf:
            # Extraer texto del PDF
            pdf_text = extract_pdf_text(uploaded_pdf)
            st.write("Texto extraído del PDF:")
            st.write(pdf_text)

            # Crear un cliente para el modelo del servicio de lenguaje en Azure
            language_client = ConversationAnalysisClient(
                ls_prediction_endpoint, AzureKeyCredential(ls_prediction_key)
            )

            cls_project = 'CLUordenadores'
            deployment_slot = 'modelo'

            # Analizar el texto extraído con el modelo CLU
            result = analyze_text_with_clu(pdf_text, language_client, cls_project, deployment_slot)

            entities = result["result"]["prediction"]["entities"]
            marca = None
            ram = None
            almacenamiento = None
            color = None
            pulgadas = None

            # Procesar las entidades extraídas
            for entity in entities:
                if entity["category"] == "Marca":
                    marca = str(entity["text"])
                elif entity["category"] == "RAM":
                    ram_match = re.search(r'\d+', str(entity["text"]))
                    if ram_match:
                        ram = ram_match.group(0)
                elif entity["category"] == "Almacenamiento":
                    almacenamiento = str(entity["text"]).split()[0]
                elif entity["category"] == "Color":
                    color = str(entity["text"]).lower()
                elif entity["category"] == "Pulgadas":
                    pulgadas = str(entity["text"]).split()[0]

            # Guardar las características en MongoDB
            if marca and ram and almacenamiento:
                collection.insert_one({
                    "marca": marca,
                    "ram": ram,
                    "almacenamiento": almacenamiento,
                    "color": color,
                    "pulgadas": pulgadas
                })

                st.write("El ordenador se ha añadido correctamente a la base de datos.")

                # Realizar una búsqueda para encontrar un ordenador con esas características
                query = {}
                if marca:
                    query["marca"] = marca
                if ram:
                    query["ram"] = ram
                if almacenamiento:
                    almacenamiento_int = parse_storage(almacenamiento)
                    query["almacenamiento"] = almacenamiento_int
                if color:
                    query["color"] = color
                if pulgadas:
                    query["pulgadas"] = pulgadas

                results = list(collection.find(query))

                if results:
                    st.write("Ordenadores encontrados:")
                    for doc in results:
                        st.write(f"Marca: {doc['marca']}, RAM: {doc['ram']}, Almacenamiento: {doc['almacenamiento']}, Color: {doc['color']}, Pulgadas: {doc['pulgadas']}")
                else:
                    st.write("No se encontraron ordenadores que coincidan con las características.")

        # Pedir entrada al usuario para buscar un ordenador en la base de datos
        user_input = st.text_input("¿Qué tipo de ordenador buscas?", "")

        if user_input:
            # Crear un cliente para el modelo del servicio de lenguaje en Azure
            language_client = ConversationAnalysisClient(
                ls_prediction_endpoint, AzureKeyCredential(ls_prediction_key)
            )

            cls_project = 'CLUordenadores'
            deployment_slot = 'modelo'

            # Analizar la consulta del usuario con CLU
            result = analyze_text_with_clu(user_input, language_client, cls_project, deployment_slot)

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
                query["pulgadas"] = pulgadas
            if marca:
                query["marca"] = marca
            if ram:
                query["ram"] = ram
            if color:  # Si hay color, agregarlo a la consulta
                query["color"] = color

            if almacenamiento:
                almacenamiento_int = parse_storage(almacenamiento)
                if almacenamiento_int:
                    if comparacion_almacenamiento == "más de":
                        query["almacenamiento"] = {"$gt": almacenamiento_int}
                    elif comparacion_almacenamiento == "menos de":
                        query["almacenamiento"] = {"$lt": almacenamiento_int}
                    else:
                        query["almacenamiento"] = almacenamiento_int

            results = list(collection.find(query))

            if results:
                for doc in results:
                    modelo = doc.get("modelo", "N/A")
                    st.subheader(modelo)  # Mostrar el modelo en grande

                    # Mostrar las propiedades como una lista ordenada
                    st.write("### Propiedades del Ordenador:")
                    detalles = []
                    for key in ["marca", "ram", "almacenamiento", "color", "pulgadas"]:
                        valor = doc.get(key, 'N/A')
                        if valor != 'N/A':
                            detalles.append(f"- {key.capitalize()}: {valor}")

                    # Mostrar las propiedades
                    st.write("\n".join(detalles))

                    st.write("---")
            else:
                st.write("No se encontraron ordenadores que coincidan con tu búsqueda.")

    except Exception as ex:
        st.error(f"Error: {ex}")

if __name__ == "__main__":  
    main()
