from pathlib import Path
import pyvips


class ThumbnailService:
    @staticmethod
    def generate_thumbnail(
        master_path: Path,
        project_root: Path,
        page_id: str,
        target_long_edge: int = 320
    ) -> Path:
        """
        Generate web preview thumbnail using pyvips.
        Outputs to project/cache/thumbnails/{page_id}.jpg
        Returns relative path.
        """
        thumb_dir = project_root / "cache" / "thumbnails"
        thumb_dir.mkdir(parents=True, exist_ok=True)

        target_file = thumb_dir / f"{page_id}.jpg"
        
        # pyvips thumbnail operates efficiently with shrink-on-load
        thumb = pyvips.Image.thumbnail(str(master_path), target_long_edge)
        thumb.jpegsave(str(target_file), Q=85, strip=True)

        return Path("cache") / "thumbnails" / f"{page_id}.jpg"
