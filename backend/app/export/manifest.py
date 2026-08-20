import csv
import json
from pathlib import Path
from typing import Any, Dict, List
from app.export.models import RegionExportMetadata


def write_region_metadata_json(meta: RegionExportMetadata, output_path: Path):
    """Writes individual JSON sidecar for an exported region."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = meta.model_dump(mode="json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def generate_catalog_csv(records: List[Dict[str, Any]], output_path: Path):
    """Generates master catalog.csv summarizing all exported illustrations."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not records:
        return

    fieldnames = [
        "page_sequence",
        "illustration_sequence",
        "name",
        "width_px",
        "height_px",
        "dpi",
        "archive_file",
        "clean_file",
        "vector_file",
    ]

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow({k: r.get(k, "") for k in fieldnames})
