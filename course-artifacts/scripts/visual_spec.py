from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union


BUILDER_VERSION = "1.1.0"
SUPPORTED_SPEC_VERSION_PREFIXES = ("1.1", "v1.1")


class VisualSpecValidationError(ValueError):
    pass


def _script_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def schema_path_v1_1() -> str:
    return os.path.abspath(os.path.join(_script_dir(), "..", "spec", "visual_spec_v1_1.schema.json"))


def load_schema_v1_1() -> Dict[str, Any]:
    path = schema_path_v1_1()
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def json_canonical_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_spec_hash(data: Dict[str, Any]) -> str:
    return sha256_text(json_canonical_dumps(data))


def _path_to_str(path: Iterable[Union[str, int]]) -> str:
    parts: List[str] = []
    for p in path:
        if isinstance(p, int):
            if not parts:
                parts.append(f"[{p}]")
            else:
                parts[-1] = f"{parts[-1]}[{p}]"
        else:
            parts.append(str(p))
    return ".".join(parts) if parts else "<root>"


def _format_jsonschema_error(err: Any) -> str:
    path = _path_to_str(err.path)
    if getattr(err, "validator", None) == "required":
        # Common shape: "'answer' is a required property"
        missing: Optional[str] = None
        msg = getattr(err, "message", "")
        if "'" in msg:
            chunks = msg.split("'")
            if len(chunks) >= 2:
                missing = chunks[1]
        if missing:
            if path == "<root>":
                path = missing
            else:
                path = f"{path}.{missing}"
            return f"{path}: missing required field"
    return f"{path}: {getattr(err, 'message', str(err))}"


def normalize_visual_spec(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Backward-compatible normalization:
    - meta.generated_at -> meta.date (if date missing)
    - sections[*].content -> sections[*].content_md (if content_md missing)
    - lecture_notes[*].content -> lecture_notes[*].content_md (if content_md missing)
    - exports.docx -> exports.lecture_docx (if lecture_docx missing)
    """
    if not isinstance(data, dict):
        raise VisualSpecValidationError("<root>: expected an object")

    meta = data.get("meta") or {}
    if isinstance(meta, dict):
        if "date" not in meta and "generated_at" in meta:
            meta["date"] = meta.get("generated_at")
        data["meta"] = meta

    exports = data.get("exports") or {}
    if isinstance(exports, dict):
        if "lecture_docx" not in exports and "docx" in exports:
            exports["lecture_docx"] = exports.get("docx")
        data["exports"] = exports

    for list_key in ("sections", "lecture_notes"):
        items = data.get(list_key)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            if "content_md" not in item and "content" in item:
                item["content_md"] = item.get("content")

    return data


def validate_visual_spec_v1_1(data: Dict[str, Any], *, schema: Optional[Dict[str, Any]] = None) -> None:
    try:
        from jsonschema import Draft202012Validator
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Missing dependency: jsonschema. Install minimal requirements (see requirements.min.txt)."
        ) from e

    schema_obj = schema or load_schema_v1_1()
    validator = Draft202012Validator(schema_obj)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    if errors:
        raise VisualSpecValidationError(_format_jsonschema_error(errors[0]))

    # Extra checks with clearer messages
    sections = data.get("sections") or []
    if isinstance(sections, list) and len(sections) < 4:
        raise VisualSpecValidationError(f"sections: expected >= 4 items, got {len(sections)}")

    qb = data.get("quiz_bank") or {}
    if isinstance(qb, dict):
        for k in ("single_choice", "fill_blank", "true_false"):
            arr = qb.get(k)
            if not isinstance(arr, list):
                raise VisualSpecValidationError(f"quiz_bank.{k}: missing required field")
            if len(arr) != 10:
                raise VisualSpecValidationError(f"quiz_bank.{k}: expected 10 items, got {len(arr)}")


def get_meta_title(data: Dict[str, Any]) -> str:
    meta = data.get("meta") or {}
    if isinstance(meta, dict):
        title = meta.get("title")
        if isinstance(title, str) and title.strip():
            return title.strip()
    return "课程"


def get_meta_date(data: Dict[str, Any]) -> str:
    meta = data.get("meta") or {}
    if isinstance(meta, dict):
        for k in ("date", "generated_at"):
            v = meta.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return datetime.now().strftime("%Y-%m-%d")


def get_meta_watermark(data: Dict[str, Any]) -> str:
    meta = data.get("meta") or {}
    if isinstance(meta, dict):
        v = meta.get("watermark")
        if isinstance(v, str) and v.strip():
            return v.strip()
    return "holo-tutor-agent"


def get_content_md(obj: Dict[str, Any]) -> str:
    v = obj.get("content_md")
    if isinstance(v, str) and v.strip():
        return v
    v2 = obj.get("content")
    if isinstance(v2, str) and v2.strip():
        return v2
    return ""


def sanitize_filename_component(name: str) -> str:
    """
    Windows-safe filename component:
    - strips invalid characters
    - trims whitespace and trailing dots
    """
    invalid = '<>:"/\\\\|?*'
    out = "".join("_" if ch in invalid else ch for ch in name)
    out = out.strip().rstrip(".")
    return out or "output"


def parse_only_list(value: Optional[str]) -> Optional[List[str]]:
    if not value:
        return None
    items = [v.strip() for v in value.split(",") if v.strip()]
    return items or None


def normalize_exports(raw_exports: Any, *, only: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    exports: Dict[str, Any] = raw_exports if isinstance(raw_exports, dict) else {}

    # Defaults: keep zip on, pdf off (can be enabled by spec)
    norm = {
        "html": bool(exports.get("html", True)),
        "lecture_docx": bool(exports.get("lecture_docx", exports.get("docx", True))),
        "quiz_docx": bool(exports.get("quiz_docx", True)),
        "pdf": bool(exports.get("pdf", False)),
        "zip": bool(exports.get("zip", True)),
        "zip_name": exports.get("zip_name") if isinstance(exports.get("zip_name"), str) else "bundle.zip",
    }

    if only is not None:
        allowed = {"html", "lecture_docx", "quiz_docx", "pdf", "zip"}
        unknown = [x for x in only if x not in allowed]
        if unknown:
            raise VisualSpecValidationError(f"--only: unknown export(s): {', '.join(unknown)}")
        for k in ("html", "lecture_docx", "quiz_docx", "pdf", "zip"):
            norm[k] = False
        for k in only:
            norm[k] = True

    return norm


def resolve_outdir(json_path: str, outdir: str) -> str:
    if os.path.isabs(outdir):
        return outdir
    # Relative outdir is resolved against input JSON folder (not CWD) for stability.
    base = os.path.dirname(os.path.abspath(json_path))
    return os.path.abspath(os.path.join(base, outdir))
