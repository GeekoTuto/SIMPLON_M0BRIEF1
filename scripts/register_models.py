from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import mlflow
from mlflow import pyfunc
from mlflow.tracking import MlflowClient
from sklearn.metrics import accuracy_score, f1_score
from langdetect import DetectorFactory, detect
from transformers import pipeline


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5001")
DEFAULT_STAGE = os.environ.get("FASTIA_MLFLOW_STAGE", "Production")

CLASSIFICATION_NAME = "fastia-classification"
LANGUAGE_NAME = "fastia-language"
SENTIMENT_NAME = "fastia-sentiment"

CLASSIFICATION_MODEL_DIR = PROJECT_ROOT / "model_run3"
LANGUAGE_MODEL_FILE = PROJECT_ROOT / "lid.176.bin"
LANGUAGE_EVAL_FILE = PROJECT_ROOT / "data" / "eval" / "langue_eval_200.jsonl"
SENTIMENT_EVAL_FILE = PROJECT_ROOT / "data" / "eval" / "sentiment_eval_50 copy.jsonl"

SENTIMENT_MODEL_ID = "nlptown/bert-base-multilingual-uncased-sentiment"
SENTIMENT_MAP = {
    "1 star": "negatif",
    "2 stars": "negatif",
    "3 stars": "neutre",
    "4 stars": "positif",
    "5 stars": "positif",
}


class MetadataPyfuncModel(pyfunc.PythonModel):
    def __init__(self, model_name: str, info: dict[str, Any]):
        self.model_name = model_name
        self.info = info

    def predict(self, context, model_input, params=None):
        _ = (context, params)
        size = len(model_input) if hasattr(model_input, "__len__") else 1
        return [{"model": self.model_name, "info": self.info}] * size


def normalize_sentiment(label: str) -> str:
    lowered = label.strip().lower()
    lowered = lowered.replace("é", "e")
    return lowered


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def directory_stats(path: Path) -> tuple[int, int]:
    total_bytes = 0
    total_files = 0
    for item in path.rglob("*"):
        if item.is_file():
            total_files += 1
            total_bytes += item.stat().st_size
    return total_files, total_bytes


def benchmark_language(eval_file: Path) -> dict[str, float]:
    if not eval_file.exists():
        return {"accuracy": 0.0, "f1_macro": 0.0, "samples": 0.0}

    DetectorFactory.seed = 42
    rows = read_jsonl(eval_file)
    y_true: list[str] = []
    y_pred: list[str] = []

    for row in rows:
        text = str(row.get("text", ""))
        lang = str(row.get("lang", "unknown"))
        try:
            pred = detect(text)
        except Exception:
            pred = "unknown"
        y_true.append(lang)
        y_pred.append(pred)

    if not y_true:
        return {"accuracy": 0.0, "f1_macro": 0.0, "samples": 0.0}

    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "samples": float(len(y_true)),
    }


def benchmark_sentiment(eval_file: Path, model_id: str) -> dict[str, float]:
    if not eval_file.exists():
        return {"accuracy": 0.0, "f1_macro": 0.0, "samples": 0.0}

    rows = read_jsonl(eval_file)
    if not rows:
        return {"accuracy": 0.0, "f1_macro": 0.0, "samples": 0.0}

    predictor = pipeline("sentiment-analysis", model=model_id, device=-1)
    y_true: list[str] = []
    y_pred: list[str] = []

    for row in rows:
        text = str(row.get("text", ""))
        true_sent = normalize_sentiment(str(row.get("sentiment", "neutre")))
        result = predictor(text[:512])[0]
        raw_label = str(result.get("label", "3 stars")).lower()
        pred_sent = SENTIMENT_MAP.get(raw_label, "neutre")

        y_true.append(true_sent)
        y_pred.append(pred_sent)

    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "samples": float(len(y_true)),
    }


def classification_metrics_from_env(model_dir: Path) -> dict[str, float]:
    files_count, total_bytes = directory_stats(model_dir) if model_dir.exists() else (0, 0)
    metrics: dict[str, float] = {
        "artifact_files": float(files_count),
        "artifact_size_mb": float(total_bytes) / (1024 * 1024),
    }

    metrics_file = os.environ.get("FASTIA_CLASSIFICATION_METRICS_FILE", "").strip()
    if metrics_file:
        path = Path(metrics_file)
        if path.exists() and path.is_file():
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            for key, value in payload.items():
                try:
                    metrics[key] = float(value)
                except (TypeError, ValueError):
                    continue

    for key, value in os.environ.items():
        if not key.startswith("FASTIA_CLASSIFICATION_METRIC_"):
            continue
        metric_name = key.replace("FASTIA_CLASSIFICATION_METRIC_", "").lower()
        try:
            metrics[metric_name] = float(value)
        except ValueError:
            continue

    return metrics


def maybe_create_registered_model(client: MlflowClient, name: str) -> None:
    try:
        client.create_registered_model(name)
    except Exception:
        pass


def register_model(
    *,
    client: MlflowClient,
    model_name: str,
    stage: str,
    params: dict[str, Any],
    metrics: dict[str, float],
    tags: dict[str, str],
    artifacts: dict[str, str] | None = None,
) -> str:
    with mlflow.start_run(run_name=f"register-{model_name}") as run:
        mlflow.log_params(params)
        if metrics:
            mlflow.log_metrics(metrics)
        if tags:
            mlflow.set_tags(tags)

        pyfunc.log_model(
            artifact_path="model",
            python_model=MetadataPyfuncModel(model_name, {"params": params, "tags": tags}),
            artifacts=artifacts,
        )

        model_uri = f"runs:/{run.info.run_id}/model"
        maybe_create_registered_model(client, model_name)
        version = mlflow.register_model(model_uri=model_uri, name=model_name)
        client.transition_model_version_stage(
            name=model_name,
            version=version.version,
            stage=stage,
            archive_existing_versions=False,
        )
        return str(version.version)


def parse_model_card(model_dir: Path) -> dict[str, str]:
    readme = model_dir / "README.md"
    if not readme.exists():
        return {}

    content = readme.read_text(encoding="utf-8")
    frontmatter: dict[str, str] = {}
    for line in content.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key in {"base_model", "library_name", "pipeline_tag"}:
            frontmatter[key] = value
    return frontmatter


def main() -> None:
    parser = argparse.ArgumentParser(description="Register FastIA models in MLflow Model Registry")
    parser.add_argument("--tracking-uri", default=DEFAULT_TRACKING_URI)
    parser.add_argument("--stage", default=DEFAULT_STAGE)
    args = parser.parse_args()

    mlflow.set_tracking_uri(args.tracking_uri)
    client = MlflowClient()

    cls_dataset = Path(os.environ.get("FASTIA_CLASSIFICATION_DATASET", LANGUAGE_EVAL_FILE.as_posix()))
    lang_dataset = Path(os.environ.get("FASTIA_LANGUAGE_DATASET", LANGUAGE_EVAL_FILE.as_posix()))
    sent_dataset = Path(os.environ.get("FASTIA_SENTIMENT_DATASET", SENTIMENT_EVAL_FILE.as_posix()))

    classification_params = {
        "model_family": "peft-lora",
        "model_dir": CLASSIFICATION_MODEL_DIR.as_posix(),
    }
    classification_params.update(parse_model_card(CLASSIFICATION_MODEL_DIR))
    classification_metrics = classification_metrics_from_env(CLASSIFICATION_MODEL_DIR)
    classification_tags = {
        "dataset_hash": file_sha256(cls_dataset) if cls_dataset.exists() else "missing",
        "dataset_path": cls_dataset.as_posix(),
        "benchmark_scope": "m4",
    }
    cls_version = register_model(
        client=client,
        model_name=CLASSIFICATION_NAME,
        stage=args.stage,
        params=classification_params,
        metrics=classification_metrics,
        tags=classification_tags,
        artifacts={"classification_artifacts": CLASSIFICATION_MODEL_DIR.as_posix()} if CLASSIFICATION_MODEL_DIR.exists() else None,
    )

    language_params = {
        "detector": "langdetect",
        "fallback_model": "fasttext/lid.176.bin",
        "fasttext_model_path": LANGUAGE_MODEL_FILE.as_posix(),
    }
    language_metrics = benchmark_language(lang_dataset)
    language_tags = {
        "dataset_hash": file_sha256(lang_dataset) if lang_dataset.exists() else "missing",
        "dataset_path": lang_dataset.as_posix(),
        "benchmark_scope": "m4",
    }
    lang_artifacts = {"fasttext_model": LANGUAGE_MODEL_FILE.as_posix()} if LANGUAGE_MODEL_FILE.exists() else None
    lang_version = register_model(
        client=client,
        model_name=LANGUAGE_NAME,
        stage=args.stage,
        params=language_params,
        metrics=language_metrics,
        tags=language_tags,
        artifacts=lang_artifacts,
    )

    sentiment_params = {
        "hf_model": SENTIMENT_MODEL_ID,
        "mapping": "1-2=negatif,3=neutre,4-5=positif",
    }
    sentiment_metrics = benchmark_sentiment(sent_dataset, SENTIMENT_MODEL_ID)
    sentiment_tags = {
        "dataset_hash": file_sha256(sent_dataset) if sent_dataset.exists() else "missing",
        "dataset_path": sent_dataset.as_posix(),
        "benchmark_scope": "m4",
    }
    sent_version = register_model(
        client=client,
        model_name=SENTIMENT_NAME,
        stage=args.stage,
        params=sentiment_params,
        metrics=sentiment_metrics,
        tags=sentiment_tags,
        artifacts=None,
    )

    print(f"Registered {CLASSIFICATION_NAME} version {cls_version} in stage {args.stage}")
    print(f"Registered {LANGUAGE_NAME} version {lang_version} in stage {args.stage}")
    print(f"Registered {SENTIMENT_NAME} version {sent_version} in stage {args.stage}")


if __name__ == "__main__":
    main()
