import time

import config
import fasttext
import numpy as np
import psutil
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
import torch

ft_model = fasttext.load_model(config.FASTTEXT_MODEL_PATH.as_posix())

def benchmark_fasttext(texts, labels):
    process = psutil.Process()
    mem_before = process.memory_info().rss / 1024 / 1024
    mem_GPU = torch.cuda.memory_allocated() / 1024 / 1024 if torch.cuda.is_available() else 0

    predictions = []
    times = []
     
    for text in texts:
        clean = text.replace("\n", " ")
        start = time.perf_counter()
        pred = ft_model.predict(clean)
        elapsed = time.perf_counter() - start
        lang = pred[0][0].replace("__label__", "")
        predictions.append(lang)
        times.append(elapsed)
     
    mem_after = process.memory_info().rss / 1024 / 1024
    mem_GPU_after = torch.cuda.memory_allocated() / 1024 / 1024 if torch.cuda.is_available() else 0
    cm = confusion_matrix(labels, predictions, labels=["fr", "en", "es"])
    f1 = classification_report(
        labels,
        predictions,
        labels=["fr", "en", "es"],
        output_dict=True,
    )["macro avg"]["f1-score"]

    return {
        "model": "fasttext",
         "predictions": predictions,
         "times_ms": [t * 1000 for t in times],
         "ram_peak_mb": mem_after - mem_before,
         "gpu_peak_mb": mem_GPU_after - mem_GPU,
         "accuracy": accuracy_score(labels, predictions),
         "f1_macro": f1,
         "f1_score": f1,
         "confusion_matrix": np.array(cm),
    }
