import os
import json
from dotenv import load_dotenv
from pymongo import MongoClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.textanalytics import TextAnalyticsClient

def main():
    try:
        # Get Configuration Settings
        load_dotenv()
        ai_endpoint = os.getenv('ENDPOINT_NER')
        ai_key = os.getenv('KEY_NER')
        project_name = os.getenv('PROJECT')
        deployment_name = os.getenv('DEPLOYMENT')

        # MongoDB Configuration
        client = MongoClient("mongodb+srv://javi:Mongodb123@mongodb-javi.global.mongocluster.cosmos.azure.com/?tls=true&authMechanism=SCRAM-SHA-256&retrywrites=false&maxIdleTimeMS=120000")
        db_name = "mongodb"  # Nombre de tu base de datos
        db = client[db_name]
        collection_name = "computer"  # Nombre de la colección

        # Borrar la base de datos antes de crearla de nuevo
        client.drop_database(db_name)
        print(f"✅ Base de datos {db_name} eliminada.")

        # Crear la base de datos nuevamente
        db = client[db_name]
        collection = db[collection_name]

        # Create client using endpoint and key
        credential = AzureKeyCredential(ai_key)
        ai_client = TextAnalyticsClient(endpoint=ai_endpoint, credential=credential)

        # Read each text file in the ads folder
        batchedDocuments = []
        folder = '../txt'
        files = os.listdir(folder)
        for file_name in files:
            # Read the file contents
            text = open(os.path.join(folder, file_name), encoding='utf8').read()
            batchedDocuments.append(text)

        # Extract entities
        operation = ai_client.begin_recognize_custom_entities(
            batchedDocuments,
            project_name=project_name,
            deployment_name=deployment_name
        )

        document_results = operation.result()

        # Prepare a list to store MongoDB documents
        mongo_documents = []

        for doc, custom_entities_result in zip(files, document_results):
            file_entities = {}

            if custom_entities_result.kind == "CustomEntityRecognition":
                for entity in custom_entities_result.entities:
                    category = entity.category
                    if category not in file_entities:
                        file_entities[category] = []

                    # Append entity details without confidence_score
                    file_entities[category].append({
                        "text": entity.text  # Omitiendo el confidence_score
                    })

                # Si hay solo un valor en la lista de una categoría, lo asignamos directamente
                for category, entities in file_entities.items():
                    if len(entities) == 1:
                        file_entities[category] = entities[0]['text']  # Asignamos el valor directamente, no como lista

            elif custom_entities_result.is_error is True:
                file_entities["error"] = {
                    "code": custom_entities_result.error.code,
                    "message": custom_entities_result.error.message
                }

            # Modificar la consulta para asegurarse de que se consulta como un número
            query = {}

            # Si se detecta RAM, se convierte a número
            if "RAM" in file_entities:
                # Convertir la RAM a un número entero, eliminando la palabra "GB"
                ram_value = file_entities["RAM"].replace("GB", "").strip()
                query["RAM"] = int(ram_value)  # Convertir a entero

            # Mostrar la consulta generada para depuración
            print(f"📝 Consulta generada para MongoDB: {query}")

            # Consultar en MongoDB
            results = list(collection.find(query))
            if results:
                print(f"✅ Se encontraron {len(results)} resultados.")
            else:
                print("❌ No se encontraron resultados.")

            # Add the document to the list for MongoDB
            mongo_documents.append({
                "_id": doc,  # Use the file name as the unique identifier
                "entities": file_entities
            })

        # Insert the documents into MongoDB
        collection.insert_many(mongo_documents)

        print(f"✅ Entidades insertadas correctamente en MongoDB.")

    except Exception as ex:
        print(ex)

if __name__ == "__main__":
    main()
