import hashlib
import json
import os
import zipfile
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

def sha256_of_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _determine_files(outdir: str, zip_name: str, files: Optional[Sequence[str]]) -> List[str]:
    if files is None:
        candidates: List[str] = []
        for name in os.listdir(outdir):
            p = os.path.join(outdir, name)
            if os.path.isfile(p) and name.lower() not in {zip_name.lower(), "manifest.json"}:
                candidates.append(name)
        return sorted(candidates)

    files_to_pack: List[str] = []
    for name in files:
        p = os.path.join(outdir, name)
        if os.path.isfile(p) and name.lower() != "manifest.json":
            files_to_pack.append(name)
    return sorted(set(files_to_pack))


def write_manifest(
    outdir: str,
    *,
    files: Optional[Sequence[str]],
    spec_version: str,
    builder_version: str,
    spec_hash: str,
    generated_at: Optional[str] = None,
    zip_name: Optional[str] = None,
) -> str:
    os.makedirs(outdir, exist_ok=True)

    files_list = _determine_files(outdir, zip_name or "bundle.zip", files)
    manifest: Dict[str, Any] = {
        "spec_version": spec_version,
        "builder_version": builder_version,
        "spec_hash": spec_hash,
        "generated_at": generated_at or datetime.now().isoformat(timespec="seconds"),
        "outdir": os.path.abspath(outdir),
        "zip": zip_name,
        "files": [],
    }

    for name in files_list:
        p = os.path.join(outdir, name)
        manifest["files"].append(
            {
                "name": name,
                "size": os.path.getsize(p),
                "sha256": sha256_of_file(p),
            }
        )

    manifest_path = os.path.join(outdir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return manifest_path


def pack(
    outdir: str,
    zip_name: str = "bundle.zip",
    *,
    files: Optional[Sequence[str]] = None,
    manifest_path: Optional[str] = None,
) -> Dict[str, str]:
    os.makedirs(outdir, exist_ok=True)

    files_to_pack = _determine_files(outdir, zip_name, files)
    manifest_path = manifest_path or os.path.join(outdir, "manifest.json")

    zip_path = os.path.join(outdir, zip_name)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        if os.path.isfile(manifest_path):
            z.write(manifest_path, arcname="manifest.json")
        for name in files_to_pack:
            z.write(os.path.join(outdir, name), arcname=name)

    return {"manifest": manifest_path, "zip": zip_path}
