import requests
import streamlit as st

from decouple import config

BACKEND_URL = config("BACKEND_URL")

st.set_page_config(
    page_title="Knowledge Agent",
    layout="wide"
)
st.title("Knowledge Agent ")
st.write("Ask questions about your workspace")

question = st.text_area(
    "Enter your question"
)

if st.button("Ask AI"):
    if question:
        with st.spinner("Analyzing ..."):
            response = requests.post(
                BACKEND_URL,
                json={
                    "question": question
                }
            )
            if response.status_code == 200:
                data = response.json()
                st.success("Response generated")
                st.write(data["answer"])
            else:
                st.error("Backend error")