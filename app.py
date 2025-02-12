import streamlit as st
from pymongo import MongoClient

# Conexión a la base de datos MongoDB utilizando los secretos de Streamlit
mongodb_connection_string = st.secrets["mongodb_connection_string"]
client = MongoClient(mongodb_connection_string)
db = client["nombre_de_tu_base_de_datos"]
collection = db["computers"]  # Colección donde están los datos de los ordenadores

# Función para consultar la base de datos y obtener información de los ordenadores
def get_computer_info(query):
    # Realizar la consulta en MongoDB utilizando la cadena de búsqueda del usuario
    computer_info = collection.find({"$text": {"$search": query}})
    computer_list = list(computer_info)  # Convertir el cursor en lista
    if computer_list:
        return computer_list
    else:
        return "No se encontró información relacionada con la consulta."

# Interfaz de Streamlit
st.title("Consulta de Ordenadores")

# Input del usuario
user_query = st.text_input("¿Qué quieres saber sobre los ordenadores?", "")

if user_query:
    # Mostrar la consulta que se está realizando
    st.subheader(f"Realizando la consulta: {user_query}")
    
    # Consultar la base de datos para obtener información
    computer_info = get_computer_info(user_query)
    
    if isinstance(computer_info, list):
        st.subheader("Resultados de la consulta:")
        for computer in computer_info:
            st.write(computer)
    else:
        st.write(computer_info)
