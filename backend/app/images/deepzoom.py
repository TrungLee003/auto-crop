from pathlib import Path
import pyvips


class DeepZoomService:
    @staticmethod
    def generate_dzi(
        master_path: Path,
        project_root: Path,
        page_id: str,
        tile_size: int = 256,
        overlap: int = 1,
        suffix: str = ".jpeg[Q=85]"
    ) -> Path:
        """
        Generate DeepZoom pyramid using pyvips dzsave.
        Outputs to project/cache/deepzoom/{page_id}.dzi and {page_id}_files/
        Returns relative path to .dzi file.
        """
        dzi_dir = project_root / "cache" / "deepzoom"
        dzi_dir.mkdir(parents=True, exist_ok=True)

        target_base = dzi_dir / page_id
        
        # Open master image
        img = pyvips.Image.new_from_file(str(master_path))
        
        # Ensure image is in sRGB / 8-bit format for standard web pyramid tiles
        if img.interpretation in (pyvips.Interpretation.SCRGB, pyvips.Interpretation.RGB16, pyvips.Interpretation.GREY16):
            img = img.colourspace(pyvips.Interpretation.SRGB)
        elif img.format not in ("uchar",):
            img = img.cast("uchar")

        # Run dzsave
        img.dzsave(
            str(target_base),
            tile_size=tile_size,
            overlap=overlap,
            suffix=suffix,
            strip=True
        )

        return Path("cache") / "deepzoom" / f"{page_id}.dzi"
