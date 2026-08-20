import mimetypes
from pathlib import Path
from typing import Optional, Tuple
from fastapi.responses import FileResponse, Response
from app.project.service import project_service


class TileServer:
    @staticmethod
    def get_dzi_file(project_id: str, page_id: str) -> Optional[Path]:
        """Return absolute path to .dzi file."""
        project = project_service.get_project(project_id)
        if not project:
            return None

        project_root = Path(project.root_path)
        dzi_path = project_root / "cache" / "deepzoom" / f"{page_id}.dzi"
        if dzi_path.is_file():
            return dzi_path
        return None

    @staticmethod
    def get_tile_file(project_id: str, page_id: str, tile_rel_path: str) -> Optional[Path]:
        """Return absolute path to a tile image or DZI descriptor."""
        project = project_service.get_project(project_id)
        if not project:
            return None

        project_root = Path(project.root_path)
        deepzoom_dir = project_root / "cache" / "deepzoom"
        
        # Check direct DZI file
        if tile_rel_path.endswith(".dzi"):
            dzi_path = deepzoom_dir / f"{page_id}.dzi"
            if dzi_path.is_file():
                return dzi_path

        # 1. Direct path inside cache/deepzoom (e.g. "{page_id}_files/10/0_0.jpeg")
        direct_path = deepzoom_dir / tile_rel_path
        if direct_path.is_file():
            return direct_path

        # 2. Check if tile_rel_path starts with "{page_id}_files/"
        prefix = f"{page_id}_files/"
        if tile_rel_path.startswith(prefix):
            sub_path = tile_rel_path[len(prefix):]
            sub_file = deepzoom_dir / f"{page_id}_files" / sub_path
            if sub_file.is_file():
                return sub_file

        # 3. If tile_rel_path is only level/col_row.jpeg (e.g. "10/0_0.jpeg")
        files_path = deepzoom_dir / f"{page_id}_files" / tile_rel_path
        if files_path.is_file():
            return files_path

        return None

    @staticmethod
    def serve_tile(project_id: str, page_id: str, tile_rel_path: str) -> Response:
        """Serve a tile or DZI descriptor file with proper Content-Type header."""
        path = TileServer.get_tile_file(project_id, page_id, tile_rel_path)
        if not path or not path.is_file():
            return Response(status_code=404, content="Tile not found")

        if path.suffix.lower() == ".dzi":
            return FileResponse(str(path), media_type="application/xml")
        
        media_type, _ = mimetypes.guess_type(str(path))
        return FileResponse(str(path), media_type=media_type or "image/jpeg")
