import numpy as np
import torch
from loguru import logger
from transformers import (
    SegformerImageProcessor, 
    SegformerForSemanticSegmentation,
    BlipProcessor,
    BlipForConditionalGeneration,
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
)
from PIL import Image
import streamlit as st

# -------------------------
# Charger les modèles
# -------------------------
@st.cache_resource
def load_models():
    segformer_processor = SegformerImageProcessor.from_pretrained(
        "nvidia/segformer-b0-finetuned-ade-512-512"
    )
    segformer_model = SegformerForSemanticSegmentation.from_pretrained(
        "nvidia/segformer-b0-finetuned-ade-512-512"
    )
    
    blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
    
    summarizer_tokenizer = AutoTokenizer.from_pretrained("sshleifer/distilbart-cnn-12-6")
    summarizer_model = AutoModelForSeq2SeqLM.from_pretrained("sshleifer/distilbart-cnn-12-6")
    
    return segformer_processor, segformer_model, blip_processor, blip_model, summarizer_tokenizer, summarizer_model

processor, model, blip_processor, blip_model, tokenizer, summarizer_model = load_models()

# -------------------------
# Interface Streamlit
# -------------------------
st.title("Segmentation d'image avec description et résumé")

uploaded_file = st.file_uploader("Choisir une image", type=["jpg", "png", "jpeg"])

if uploaded_file:
    image = Image.open(uploaded_file).convert("RGB")
    st.image(image, caption="Image originale", use_container_width=True)

    # -------------------------
    # Segmentation avec Segformer
    # -------------------------
    logger.info("Segmentation de l'image avec Segformer...")
    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
    logits = outputs.logits

    upsampled_logits = torch.nn.functional.interpolate(
        logits,
        size=image.size[::-1],
        mode="bilinear",
        align_corners=False,
    )

    segmentation_map = upsampled_logits.argmax(dim=1)[0].cpu().numpy()
    unique_ids, counts = np.unique(segmentation_map, return_counts=True)
    sorted_ids = unique_ids[np.argsort(counts)[::-1]][:5]  # top 5 classes
    total_pixels = segmentation_map.size

    # Palette de couleurs pour overlay
    palette = np.zeros((model.config.num_labels, 3), dtype=np.uint8)
    for i in range(model.config.num_labels):
        palette[i] = [(i * 37) % 255, (i * 67) % 255, (i * 97) % 255]
    
    colored_map = palette[segmentation_map]
    img_array_float = np.array(image, dtype=np.float32)
    overlay = (0.5 * img_array_float + 0.5 * colored_map).astype(np.uint8)

    st.subheader("Segmentation :")
    st.image(Image.fromarray(overlay), caption="Carte de segmentation", use_container_width=True)

    st.subheader("Top 5 classes détectées :")
    for segment_id in sorted_ids:
        percentage = (counts[unique_ids == segment_id][0] / total_pixels) * 100
        label_name = model.config.id2label.get(int(segment_id), f"Classe {segment_id}")
        st.write(f"- {label_name}: {percentage:.1f}%")

    # -------------------------
    # Descriptions par segment (réalistes)
    # -------------------------
    st.subheader("Descriptions par segment :")
    with st.spinner("Génération des descriptions..."):
        logger.info("Génération des descriptions segment par segment avec BLIP...")

        h, w = segmentation_map.shape
        min_pixels = 0.02 * (h * w)  # ignorer les petits segments <2%

        for segment_id in sorted_ids:
            mask = segmentation_map == segment_id
            if mask.sum() < min_pixels:
                continue

            # Bounding box du segment + contexte
            ys, xs = np.where(mask)
            y1, y2 = max(0, ys.min() - 5), min(h, ys.max() + 5)
            x1, x2 = max(0, xs.min() - 5), min(w, xs.max() + 5)

            segment_crop = image.crop((x1, y1, x2, y2))

            # Générer la description BLIP
            blip_inputs = blip_processor(images=segment_crop, return_tensors="pt")
            with torch.no_grad():
                blip_output = blip_model.generate(**blip_inputs, max_new_tokens=40)
            segment_caption = blip_processor.decode(blip_output[0], skip_special_tokens=True)

            label_name = model.config.id2label.get(int(segment_id), f"Classe {segment_id}")
            st.write(f"- {label_name}: {segment_caption}")

    # -------------------------
    # Résumé global avec DistilBART
    # -------------------------
    st.subheader("Résumé global de l'image :")
    with st.spinner("Génération du résumé..."):
        logger.info("Génération du résumé global avec DistilBART...")

        # Description globale BLIP pour le résumé
        blip_inputs = blip_processor(images=image, return_tensors="pt")
        with torch.no_grad():
            blip_output = blip_model.generate(**blip_inputs, max_new_tokens=40)
        global_caption = blip_processor.decode(blip_output[0], skip_special_tokens=True)

        top_classes_text = ", ".join(
            model.config.id2label.get(int(sid), f"Classe {sid}") for sid in sorted_ids
        )

        summary_input_text = f"Image shows: {global_caption}. Main objects: {top_classes_text}."

        summary_inputs = tokenizer(
            summary_input_text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        )
        with torch.no_grad():
            summary_output = summarizer_model.generate(
                **summary_inputs,
                max_new_tokens=50,
                num_beams=3,
                no_repeat_ngram_size=2,
            )
        summary = tokenizer.decode(summary_output[0], skip_special_tokens=True)
        st.write(summary)