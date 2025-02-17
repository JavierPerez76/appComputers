def parse_price(precio):
    # Extract price value (assuming format '3.849,00' for example)
    match = re.match(r'(\d+\.?\d*)\s*[,\.]?\d*\s*$', precio)
    if match:
        return float(match.group(1).replace(",", "."))
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
            color = None  # Añadimos una variable para el color
            codigo = None  # Variable para el código
            comparacion_precio = None
            precio = None

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
                elif entity["category"] == "Codigo":  # Detectar código
                    codigo = str(entity["text"])
                elif entity["category"] == "Precio":  # Detectar precio
                    precio = str(entity["text"]).split()[0]
                elif entity["category"] == "ComparacionPrecio":  # Comparación de precio
                    comparacion_precio = str(entity["text"]).lower()

            query = {}
            if pulgadas:
                query["entities.Pulgadas"] = pulgadas
            if marca:
                query["entities.Marca"] = marca
            if ram:
                query["entities.RAM"] = ram
            if color:  # Si hay color, agregarlo a la consulta
                query["entities.Color"] = color
            if codigo:  # Si hay código, agregarlo a la consulta
                query["entities.Codigo"] = codigo

            if almacenamiento:
                almacenamiento_int = parse_storage(almacenamiento)
                if almacenamiento_int:
                    if comparacion_almacenamiento == "más de":
                        query["entities.Almacenamiento"] = {"$gt": almacenamiento_int}
                    elif comparacion_almacenamiento == "menos de":
                        query["entities.Almacenamiento"] = {"$lt": almacenamiento_int}
                    else:
                        query["entities.Almacenamiento"] = almacenamiento_int

            # Si se especifica un precio y una comparación
            if precio:
                precio_float = parse_price(precio)
                if precio_float:
                    if comparacion_precio == "menos de":
                        query["entities.Precio"] = {"$lt": precio_float}
                    elif comparacion_precio == "más de":
                        query["entities.Precio"] = {"$gt": precio_float}
                    else:
                        query["entities.Precio"] = precio_float

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
