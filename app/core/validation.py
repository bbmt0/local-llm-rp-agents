import re 
from pathlib import Path 
from fastapi import HTTPException, status
import logging

ID_PATTERN = re.compile(r"^[a-zA-Z0-9\-_]+$")
logger = logging.getLogger(__name__)


def validation_id(id: str, id_type: str = "ID") -> str: 
    if not ID_PATTERN.match(id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid: {id_type}"
        )
        return id 
    
def build_path(base_dir: str, id: str, extension: str = ".json") -> Path: 
    validated_id = validation_id(id)
    path = Path(base_dir) / f"{validated_id}{extension}"
    resolved_path = path.resolve()
    if not str (resolved_path).startswith(str(Path(base_dir).resolve())):
        logger.warning(f"Invalid path {resolved_path}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid path: directory traversal detected."
        )
        return resolved_path