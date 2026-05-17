import time

import psutil
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import torch

def benchmark_sentiment_model(model_pipeline, mapping, texts, labels, model_name):
    process = psutil.Process()
    mem_before = process.memory_info().rss / 1024 / 1024
    mem_GPU = torch.cuda.memory_allocated() / 1024 / 1024 if torch.cuda.is_available() else 0
    predictions = []
    times = []

    for i, text in enumerate(texts):
        start = time.perf_counter()
        result = model_pipeline(text[:512], truncation=True)
        elapsed = time.perf_counter() - start
        raw_label = result[0]["label"]
        mapped = mapping.get(raw_label, "neutre")
        predictions.append(mapped)
        times.append(elapsed)
        # Affichage du label attendu et de la prédiction
        print(f"Texte {i}: label attendu = {labels[i]}, prédiction = {mapped} (raw: {raw_label})")

    mem_after = process.memory_info().rss / 1024 / 1024
    mem_GPU_after = torch.cuda.memory_allocated() / 1024 / 1024 if torch.cuda.is_available() else 0
    cm = confusion_matrix(labels, predictions, labels=["positif", "neutre", "négatif"])
    return {
        "model": model_name,
        "predictions": predictions,
        "times_ms": [t * 1000 for t in times],
        "ram_peak_mb": mem_after - mem_before,
        "gpu_peak_mb": mem_GPU_after - mem_GPU,
        "accuracy": accuracy_score(labels, predictions),
        "robustesse": 0,
        "f1_macro": classification_report(labels, predictions, labels=["positif", "neutre", "négatif"], output_dict=True)["macro avg"]["f1-score"],
        "confusion_matrix": cm,
    }