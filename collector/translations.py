"""Optional, local machine translations. Original observations are never edited.

The cache is separate from the evidence database and keyed by the exact source
text, language, model and revision. Inference runs locally; only the initial
public model download needs network access (never the collection proxy).
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from .publish import atomic_write, canonical

MODEL = "Helsinki-NLP/OPUS-MT"
REVISION = "worldview-language-models-1"
# Only publish the language-specific model families checked on pilot headlines.
# The smaller mul-en model produced misleading JA/HI and European headlines.
ROMANCE_MODEL = ("Helsinki-NLP/opus-mt-ROMANCE-en", "e9ca9975e3972afd80732f08ce01d3a1339f47f8")
LANGUAGE_MODELS = {"fr": ROMANCE_MODEL, "es": ROMANCE_MODEL, "pt": ROMANCE_MODEL,
                   "de": ("Helsinki-NLP/opus-mt-de-en", "1a922f3b32a8e809e17a47d4b32142d8105924e5")}
SUPPORTED_LANGUAGES = frozenset(LANGUAGE_MODELS)


class TranslationCache:
    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=30)
        self.db.execute("""CREATE TABLE IF NOT EXISTS translations (
            original TEXT NOT NULL, source_language TEXT NOT NULL,
            model TEXT NOT NULL, revision TEXT NOT NULL, english TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status='translated'),
            PRIMARY KEY(original, source_language, model, revision))""")
        self.db.commit()

    def get(self, original, language, model, revision):
        row = self.db.execute(
            "SELECT english FROM translations WHERE original=? AND source_language=? AND model=? AND revision=?",
            (original, language, model, revision)).fetchone()
        return row[0] if row else None

    def put(self, original, language, english, model, revision):
        if not isinstance(english, str) or not english.strip():
            raise ValueError("Translation model returned empty output; no translation cached.")
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO translations VALUES(?,?,?,?,?,'translated')",
                            (original, language, model, revision, english.strip()))

    def close(self):
        self.db.close()


class LocalTranslator:
    model = MODEL
    revision = REVISION
    supported_languages = SUPPORTED_LANGUAGES

    def __init__(self, local_files_only=False):
        self.local_files_only = local_files_only
        self._model = self._tokenizer = None
        self._loaded_model = None

    def provenance(self, language):
        return LANGUAGE_MODELS[language]

    def _load(self, language):
        model, revision = self.provenance(language)
        if self._loaded_model == model:
            return
        self._model = self._tokenizer = None
        try:
            import torch
            from transformers import AutoModelForSeq2SeqLM, MarianTokenizer
            self._tokenizer = MarianTokenizer.from_pretrained(
                model, revision=revision, local_files_only=self.local_files_only)
            self._model = AutoModelForSeq2SeqLM.from_pretrained(
                model, revision=revision, local_files_only=self.local_files_only)
            self._model.eval()
            self._loaded_model = model
            # CPU keeps this optional path portable; limit oversubscription.
            torch.set_num_threads(min(4, torch.get_num_threads()))
        except Exception:
            raise ValueError("Local translation model unavailable; install .[translations] and download the pinned model once. Existing translation export preserved.") from None

    def translate(self, texts, language):
        self._load(language)
        import torch
        # Never silently truncate source text. Published headlines fit this cap.
        encoded = self._tokenizer(texts, return_tensors="pt", padding=True, truncation=False)
        if encoded["input_ids"].shape[1] > 512:
            raise ValueError("Translation input exceeds model context; original text preserved.")
        with torch.inference_mode():
            generated = self._model.generate(**encoded, max_length=256, num_beams=4)
        return self._tokenizer.batch_decode(generated, skip_special_tokens=True)


def recording_texts(recording):
    """Return exact display text with its recorded language, without mutation."""
    countries = {c["code"]: c.get("language", "und") for c in recording.get("countries", [])}
    texts = set()
    # Topic labels may come from an item in another country's snapshot.
    recorded_languages = {}
    for snapshot in recording.get("snapshots", []):
        for topic in snapshot.get("topics", []):
            for item in topic.get("items", []):
                if item.get("title") and item.get("language"):
                    recorded_languages.setdefault(item["title"], item["language"])
    for snapshot in recording.get("snapshots", []):
        fallback = "en" if snapshot.get("profile") == "english" else countries.get(snapshot["country"], "und")
        for topic in snapshot.get("topics", []):
            item_languages = {}
            for item in topic.get("items", []):
                language = item.get("language") or fallback
                title = item.get("title")
                if isinstance(title, str) and title.strip():
                    texts.add((title, language))
                    item_languages.setdefault(title, language)
            for text in [topic.get("label"), *topic.get("aliases", [])]:
                if isinstance(text, str) and text.strip():
                    texts.add((text, item_languages.get(text, recorded_languages.get(text, fallback))))
    return sorted(texts, key=lambda pair: (pair[1], pair[0]))


def build_translations(recording, cache, translator=None, batch_size=8, progress=None):
    if batch_size < 1:
        raise ValueError("Translation batch size must be positive.")
    translator = translator or LocalTranslator()
    entries, pending, unsupported, failures = {}, {}, set(), []
    for original, language in recording_texts(recording):
        language = language.lower().split("-")[0]
        if language == "en":
            continue
        if language not in translator.supported_languages:
            unsupported.add(language)
            continue
        model, revision = translator.provenance(language) if hasattr(translator, "provenance") else (translator.model, translator.revision)
        english = cache.get(original, language, model, revision)
        if english is None:
            pending.setdefault(language, []).append(original)
        else:
            entries[(original, language)] = (english, model, revision)
    for language, texts in sorted(pending.items()):
        for offset in range(0, len(texts), batch_size):
            batch = texts[offset:offset + batch_size]
            model, revision = translator.provenance(language) if hasattr(translator, "provenance") else (translator.model, translator.revision)
            # Model load failure is fatal: retain the previous complete export.
            if isinstance(translator, LocalTranslator):
                translator._load(language)
            try:
                outputs = translator.translate(batch, language)
                if len(outputs) != len(batch) or any(not isinstance(x, str) or not x.strip() for x in outputs):
                    raise ValueError("Invalid model output")
            except Exception:
                failures.extend({"original": text, "sourceLanguage": language, "status": "failed"} for text in batch)
                continue
            for original, english in zip(batch, outputs):
                cache.put(original, language, english, model, revision)
                entries[(original, language)] = (english.strip(), model, revision)
            if progress:
                progress(language, min(offset + len(batch), len(texts)), len(texts))
    result = {"schemaVersion": 1, "targetLanguage": "en", "model": translator.model,
              "modelRevision": translator.revision, "translationKind": "local-machine-translation",
              "entries": [{"original": original, "sourceLanguage": language, "english": english,
                           "status": "translated", "model": model, "modelRevision": revision}
                          for (original, language), (english, model, revision) in sorted(entries.items())],
              "unsupportedLanguages": sorted(unsupported)}
    if failures:
        result["failures"] = failures
    return result


def translate_publication(destination, cache_path, local_files_only=False, batch_size=8):
    destination = Path(destination)
    manifest = json.loads((destination / "manifest.json").read_text())
    recording_path = destination / manifest["datasetVersion"] / "recording.json"
    return translate_recording(recording_path, destination / "translations.json", cache_path,
                               local_files_only, batch_size)


def translate_recording(recording_path, output, cache_path, local_files_only=False, batch_size=8):
    recording = json.loads(Path(recording_path).read_text())
    cache = TranslationCache(cache_path)
    try:
        result = build_translations(recording, cache, LocalTranslator(local_files_only), batch_size,
                                    lambda lang, done, total: print(f"translate: {lang} {done}/{total}", file=sys.stderr, flush=True))
        atomic_write(output, canonical(result))
        return {"translated": len(result["entries"]), "unsupportedLanguages": result["unsupportedLanguages"],
                "failed": len(result.get("failures", [])), "model": result["model"], "modelRevision": result["modelRevision"]}
    finally:
        cache.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Translate published Worldview headlines locally; preserve originals")
    parser.add_argument("--input", type=Path, help="Recording JSON; defaults to the current output manifest")
    parser.add_argument("--output", type=Path, default=Path("public/data/translations.json"))
    parser.add_argument("--cache", type=Path, default=Path(".worldview/translations.sqlite"))
    parser.add_argument("--local-files-only", action="store_true", help="Forbid model downloads; cached translations need no model")
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args(argv)
    try:
        if args.input:
            result = translate_recording(args.input, args.output, args.cache, args.local_files_only, args.batch_size)
        else:
            destination = args.output.parent
            manifest = json.loads((destination / "manifest.json").read_text())
            result = translate_recording(destination / manifest["datasetVersion"] / "recording.json",
                                         args.output, args.cache, args.local_files_only, args.batch_size)
        print(json.dumps(result, indent=2))
        return 0
    except Exception as error:
        print("translate: " + (str(error) if isinstance(error, ValueError) else type(error).__name__) + "; originals preserved.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
