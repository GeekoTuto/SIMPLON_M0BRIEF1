from langdetect import detect, DetectorFactory
import time
from sklearn.metrics import (
    accuracy_score,
    classification_report
)
import psutil

DetectorFactory.seed = 42


def benchmark_langdetect(texts, labels):
    """Benchmark langdetect sur une liste de textes."""
    process = psutil.Process()
    mem_before = process.memory_info().rss / 1024 / 1024  # MB

    predictions = []
    times = []

    for text in texts:
        start = time.perf_counter()
        try:
            pred = detect(text)
        except Exception:
            pred = "unknown"
        elapsed = time.perf_counter() - start
        predictions.append(pred)
        times.append(elapsed)

    mem_after = process.memory_info().rss / 1024 / 1024

    return {
        "model": "langdetect",
        "predictions": predictions,
        "f1_macro": classification_report(labels, predictions, labels=["fr", "en", "es"], output_dict=True)["macro avg"]["f1-score"],
        "times_ms": [t * 1000 for t in times],
        "ram_peak_mb": mem_after - mem_before,
        "accuracy": accuracy_score(labels, predictions),
    }