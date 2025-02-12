import streamlit as st
from pymongo import MongoClient

client = MongoClient(st.secrets["mongodb_connection_string"])
db = client['mongodb']  # Cambia por el nombre de tu base de datos
collection = db['computers']  # Cambia por el nombre de tu colección


result = collection.find()

# Mostrar los documentos en la interfaz de Streamlit
st.title("Documentos de la Base de Datos MongoDB")

# Crear un contenedor para mostrar los documentos
if result:
    st.write("Aquí están los documentos encontrados en la colección:")
    for document in result:
        st.write(document)
else:
    st.write("No se encontraron documentos.")

# # Conexión a la base de datos MongoDB utilizando los secretos de Streamlit
# mongodb_connection_string = st.secrets["mongodb_connection_string"]
# client = MongoClient(mongodb_connection_string)
# db = client["mongodb"]
# collection = db["computers"]  # Colección donde están los datos de los ordenadores
# def show_all_documents():
#     # Encuentra todos los documentos en la colección
#     documents = collection.find()
    
#     # Mostrar los documentos en Streamlit
#     for document in documents:
#         st.write(document)

# # Mostrar la base de datos completa antes de la consulta
# st.title("Base de Datos de Ordenadores")
# st.subheader("Todos los documentos en la base de datos:")

# show_all_documents()

# # Función para consultar la base de datos y obtener información de los ordenadores
# def get_computer_info(query):
#     # Realizar la consulta en MongoDB utilizando la cadena de búsqueda del usuario
#     computer_info = collection.find({"$text": {"$search": query}})
#     computer_list = list(computer_info)  # Convertir el cursor en lista
#     if computer_list:
#         return computer_list
#     else:
#         return "No se encontró información relacionada con la consulta."

# # Interfaz de Streamlit
# st.title("Consulta de Ordenadores")

# # Input del usuario
# user_query = st.text_input("¿Qué quieres saber sobre los ordenadores?", "")

# if user_query:
#     # Mostrar la consulta que se está realizando
#     st.subheader(f"Realizando la consulta: {user_query}")
    
#     # Consultar la base de datos para obtener información
#     computer_info = get_computer_info(user_query)
    
#     if isinstance(computer_info, list):
#         st.subheader("Resultados de la consulta:")
#         for computer in computer_info:
#             st.write(computer)
#     else:
#         st.write(computer_info)
