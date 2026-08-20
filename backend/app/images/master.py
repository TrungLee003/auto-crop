import hashlib
import os
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple
import pyvips


class MasterService:
    SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}

    @staticmethod
    def is_supported_image(path: Path) -> bool:
        return path.suffix.lower() in MasterService.SUPPORTED_EXTENSIONS

    @staticmethod
    def compute_file_hash(file_path: Path) -> str:
        """
        Fast hash using file size + SHA256 of first 64KB, middle 64KB, and last 64KB for speed on multi-GB scans.
        """
        size = file_path.stat().st_size
        hasher = hashlib.sha256()
        hasher.update(str(size).encode("utf-8"))

        with open(file_path, "rb") as f:
            # Read first chunk
            hasher.update(f.read(65536))
            if size > 131072:
                # Read middle chunk
                f.seek(size // 2)
                hasher.update(f.read(65536))
                # Read last chunk
                f.seek(max(0, size - 65536))
                hasher.update(f.read(65536))

        return hasher.hexdigest()

    @staticmethod
    def get_image_metadata(image_path: Path) -> Dict[str, any]:
        """Extract metadata from an image using pyvips."""
        vips_img = pyvips.Image.new_from_file(str(image_path))
        
        # Calculate DPI from pixels/millimeter
        dpi = 300.0
        if vips_img.xres > 0:
            dpi = round(vips_img.xres * 25.4, 1)

        bit_depth = 8
        if vips_img.format in ("ushort", "short"):
            bit_depth = 16
        elif vips_img.format in ("uint", "int", "float"):
            bit_depth = 32

        return {
            "width": vips_img.width,
            "height": vips_img.height,
            "bands": vips_img.bands,
            "dpi": dpi,
            "bit_depth": bit_depth,
            "file_size_bytes": image_path.stat().st_size,
        }

    @staticmethod
    def create_master_from_source(
        source_path: Path,
        project_root: Path,
        page_id: str,
        copy_source: bool = True
    ) -> Tuple[Path, Path, Dict[str, any]]:
        """
        Processes a source image for the project:
        - If copy_source is True, copies to project/sources/{filename}
        - Creates canonical master in project/masters/{filename}
        - Returns (relative_source_path, relative_master_path, metadata)
        """
        sources_dir = project_root / "sources"
        masters_dir = project_root / "masters"
        sources_dir.mkdir(parents=True, exist_ok=True)
        masters_dir.mkdir(parents=True, exist_ok=True)

        ext = source_path.suffix.lower()
        base_name = f"{page_id}_{source_path.stem}{ext}"

        if copy_source:
            target_source = sources_dir / base_name
            shutil.copy2(source_path, target_source)
            rel_source = Path("sources") / base_name
        else:
            target_source = source_path
            rel_source = source_path # absolute or external reference

        # Create master: In Phase 1 without preprocessing, master is identical to source
        target_master = masters_dir / base_name
        if not target_master.exists():
            shutil.copy2(target_source, target_master)
        rel_master = Path("masters") / base_name

        meta = MasterService.get_image_metadata(target_master)
        meta["file_hash"] = MasterService.compute_file_hash(target_master)

        return rel_source, rel_master, meta
