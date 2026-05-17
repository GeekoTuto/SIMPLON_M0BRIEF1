import base64
import io

import requests
from loguru import logger
from PIL import Image
import streamlit as st
import os

logger.remove()
logger.add("logs/analyse_image.log", rotation="500 MB", level="INFO")

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
API_URL = os.getenv("API_IMAGE_URL", f"{API_BASE_URL}/analyse_image/")

st.title("Segmentation d'image")
api_url = st.text_input("URL API image", value=API_URL)

uploaded_file = st.file_uploader("Choisissez une image", type=["jpg", "png", "jpeg"])

if uploaded_file:
    image = Image.open(uploaded_file).convert("RGB")
    st.image(image, caption="Image originale", use_container_width=True)

    if st.button("Analyser l'image", type="secondary"):
        with st.spinner("Analyse de l'image en cours..."):
            try:
                uploaded_file.seek(0)
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                response = requests.post(api_url, files=files, timeout=300)
                response.raise_for_status()
                result = response.json()

                overlay_bytes = base64.b64decode(result["overlay_image_base64"])
                overlay_image = Image.open(io.BytesIO(overlay_bytes))

                st.subheader("Segmentation:")
                st.image(overlay_image, caption="Carte de segmentation", use_container_width=True)

                st.subheader("Top 5 des classes détectées:")
                for item in result["top_classes"]:
                    st.write(f"- {item['label']}: {item['percentage']:.1f}%")

                st.subheader("Description globale:")
                st.write(result["global_caption"])

                st.subheader("Descriptions par segment:")
                for item in result["segment_descriptions"]:
                    st.write(f"- {item['label']}: {item['caption']}")

                st.subheader("Résumé:")
                st.write(result["summary"])
                logger.info("Analyse image via API terminée")
            except requests.exceptions.ConnectionError:
                logger.error(f"Connexion impossible à l'API : URL={api_url}")
                st.error("Connexion impossible à l'API")
            except requests.exceptions.HTTPError as exc:
                logger.error(f"Erreur HTTP : {exc}")
                st.error(f"Erreur HTTP : {exc}")
            except requests.exceptions.RequestException as exc:
                logger.error(f"Erreur appel API : {exc}")
                st.error(f"Erreur appel API : {exc}")
    