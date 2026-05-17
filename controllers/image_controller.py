import base64
import io
from functools import lru_cache

import numpy as np
import torch
from fastapi import APIRouter, File, HTTPException, UploadFile
from loguru import logger
from PIL import Image
from transformers import (
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    BlipForConditionalGeneration,
    BlipProcessor,
    SegformerForSemanticSegmentation,
    SegformerImageProcessor,
)

router = APIRouter()
image_logger = logger.bind(channel="image")


@lru_cache(maxsize=1)
def load_models():
    segformer_processor = SegformerImageProcessor.from_pretrained(
        "nvidia/segformer-b0-finetuned-ade-512-512"
    )
    segformer_model = SegformerForSemanticSegmentation.from_pretrained(
        "nvidia/segformer-b0-finetuned-ade-512-512"
    )

    blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    blip_model = BlipForConditionalGeneration.from_pretrained(
        "Salesforce/blip-image-captioning-base"
    )

    summarizer_tokenizer = AutoTokenizer.from_pretrained("sshleifer/distilbart-cnn-12-6")
    summarizer_model = AutoModelForSeq2SeqLM.from_pretrained(
        "sshleifer/distilbart-cnn-12-6"
    )

    return (
        segformer_processor,
        segformer_model,
        blip_processor,
        blip_model,
        summarizer_tokenizer,
        summarizer_model,
    )


def image_to_base64(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


@router.post("/analyse_image/")
async def analyse_image(file: UploadFile = File(...)):
    if file.content_type not in {"image/jpeg", "image/png", "image/jpg"}:
        raise HTTPException(status_code=400, detail="Format image pas correct")

    try:
        file_bytes = await file.read()
        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")

        processor, model, blip_processor, blip_model, tokenizer, summarizer_model = load_models()

        image_logger.info("Travail sur l'image avec Segformer...")
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
        sorted_ids = unique_ids[np.argsort(counts)[::-1]][:5]
        total_pixels = segmentation_map.size

        palette = np.zeros((model.config.num_labels, 3), dtype=np.uint8)
        for i in range(model.config.num_labels):
            palette[i] = [(i * 37) % 255, (i * 67) % 255, (i * 97) % 255]

        colored_map = palette[segmentation_map]
        img_array_float = np.array(image, dtype=np.float32)
        overlay = (0.5 * img_array_float + 0.5 * colored_map).astype(np.uint8)
        overlay_image = Image.fromarray(overlay)

        top_classes = []
        for segment_id in sorted_ids:
            percentage = float((counts[unique_ids == segment_id][0] / total_pixels) * 100)
            label_name = model.config.id2label.get(int(segment_id), f"Classe {segment_id}")
            top_classes.append(
                {
                    "segment_id": int(segment_id),
                    "label": label_name,
                    "percentage": round(percentage, 1),
                }
            )

        blip_inputs = blip_processor(images=image, return_tensors="pt")
        with torch.no_grad():
            blip_output = blip_model.generate(**blip_inputs, max_new_tokens=40)
        global_caption = blip_processor.decode(blip_output[0], skip_special_tokens=True)

        segment_descriptions = []
        image_array = np.array(image)
        for segment_id in sorted_ids:
            mask = segmentation_map == segment_id
            if mask.sum() == 0:
                continue

            segment_array = image_array.copy()
            segment_array[~mask] = 0
            segment_image = Image.fromarray(segment_array)

            blip_inputs = blip_processor(images=segment_image, return_tensors="pt")
            with torch.no_grad():
                blip_output = blip_model.generate(**blip_inputs, max_new_tokens=40)
            segment_caption = blip_processor.decode(blip_output[0], skip_special_tokens=True)

            label_name = model.config.id2label.get(int(segment_id), f"Classe {segment_id}")
            segment_descriptions.append(
                {
                    "segment_id": int(segment_id),
                    "label": label_name,
                    "caption": segment_caption,
                }
            )

        top_classes_text = ", ".join(item["label"] for item in top_classes)
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

        image_logger.info("Fin de l'analyse image")
        return {
            "overlay_image_base64": image_to_base64(overlay_image),
            "top_classes": top_classes,
            "global_caption": global_caption,
            "segment_descriptions": segment_descriptions,
            "summary": summary,
        }
    except HTTPException:
        raise
    except Exception as exc:
        image_logger.exception(f"Erreur analyse image: {exc}")
        raise HTTPException(status_code=500, detail="Erreur interne serveur")
