import copy
import json

from collector.translations import TranslationCache, build_translations, recording_texts, translate_recording


class FakeTranslator:
    model = "fixture-model"
    revision = "fixture-revision"
    supported_languages = {"fr", "es"}

    def __init__(self):
        self.calls = []

    def translate(self, texts, language):
        self.calls.append((texts, language))
        return ["Translated fixture: " + text for text in texts]


def recording():
    return {"countries": [{"code": "FR", "language": "fr"}], "snapshots": [
        {"country": "FR", "profile": "local", "topics": [
            {"id": "topic-original", "label": "Une nouvelle école", "aliases": ["Una nueva escuela"],
             "items": [{"id": "original-item", "title": "Une nouvelle école", "language": "fr"},
                       {"id": "spanish-item", "title": "Una nueva escuela", "language": "es"},
                       {"id": "korean-item", "title": "새로운 학교", "language": "ko"},
                       {"id": "english-item", "title": "A new school", "language": "en"}]}]}]}


def test_cache_reuse_and_model_revision_provenance(tmp_path):
    source = recording()
    original = copy.deepcopy(source)
    cache = TranslationCache(tmp_path / "translations.sqlite")
    translator = FakeTranslator()
    result = build_translations(source, cache, translator, batch_size=1)
    assert source == original
    assert len(result["entries"]) == 2
    assert result["unsupportedLanguages"] == ["ko"]
    assert all(entry["status"] == "translated" and entry["modelRevision"] == translator.revision
               for entry in result["entries"])
    assert json.dumps(source) == json.dumps(original)
    translator.calls.clear()
    assert build_translations(source, cache, translator) == result
    assert translator.calls == []
    translator.revision = "new-revision"
    build_translations(source, cache, translator)
    assert len(translator.calls) == 2
    cache.close()


def test_failed_inference_never_exports_or_caches_fabricated_english(tmp_path):
    class BrokenTranslator(FakeTranslator):
        def translate(self, texts, language):
            raise RuntimeError("secret-bearing external exception")
    cache = TranslationCache(tmp_path / "translations.sqlite")
    result = build_translations(recording(), cache, BrokenTranslator())
    assert result["entries"] == []
    assert len(result["failures"]) == 2
    assert "secret-bearing" not in json.dumps(result)
    assert cache.db.execute("SELECT COUNT(*) FROM translations").fetchone()[0] == 0
    good = FakeTranslator()
    assert len(build_translations(recording(), cache, good)["entries"]) == 2
    cache.close()


def test_invalid_output_does_not_partially_cache_batch(tmp_path):
    class EmptyTranslator(FakeTranslator):
        def translate(self, texts, language):
            return [""] * len(texts)
    cache = TranslationCache(tmp_path / "translations.sqlite")
    result = build_translations(recording(), cache, EmptyTranslator())
    assert result["entries"] == []
    assert cache.db.execute("SELECT COUNT(*) FROM translations").fetchone()[0] == 0
    cache.close()


def test_cache_key_preserves_exact_text_and_source_language(tmp_path):
    cache = TranslationCache(tmp_path / "translations.sqlite")
    cache.put("Paris", "fr", "Paris", "model", "revision")
    assert cache.get("Paris", "fr", "model", "revision") == "Paris"
    assert cache.get("Paris", "es", "model", "revision") is None
    assert cache.get("Paris ", "fr", "model", "revision") is None
    assert cache.get("Paris", "fr", "other-model", "revision") is None
    assert cache.get("Paris", "fr", "model", "other-revision") is None
    cache.close()


def test_display_texts_keep_alias_item_language():
    texts = recording_texts(recording())
    assert ("Una nueva escuela", "es") in texts
    assert ("Una nueva escuela", "fr") not in texts
    assert texts.count(("Une nouvelle école", "fr")) == 1


def test_language_specific_model_is_recorded_and_cached(tmp_path):
    class RoutedTranslator(FakeTranslator):
        def provenance(self, language):
            return f"fixture-{language}-en", f"revision-{language}"
    cache = TranslationCache(tmp_path / "translations.sqlite")
    translator = RoutedTranslator()
    result = build_translations(recording(), cache, translator)
    for entry in result["entries"]:
        language = entry["sourceLanguage"]
        assert entry["model"] == f"fixture-{language}-en"
        assert entry["modelRevision"] == f"revision-{language}"
        assert cache.get(entry["original"], language, entry["model"], entry["modelRevision"]) == entry["english"]
    cache.close()


def test_model_loading_failure_preserves_previous_export(tmp_path, monkeypatch):
    import pytest
    from collector.translations import LocalTranslator
    def unavailable(self, language):
        raise ValueError("Model unavailable")
    monkeypatch.setattr(LocalTranslator, "_load", unavailable)
    source = tmp_path / "recording.json"
    source.write_text(json.dumps(recording()))
    output = tmp_path / "translations.json"
    output.write_text("previous complete export")
    with pytest.raises(ValueError, match="Model unavailable"):
        translate_recording(source, output, tmp_path / "translations.sqlite", local_files_only=True)
    assert output.read_text() == "previous complete export"
    assert json.loads(source.read_text()) == recording()
