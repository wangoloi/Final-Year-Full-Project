"""Search routes - thin layer."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.shared.database import get_db
from api.shared.dependencies import get_current_user
from api.models import User
from api.modules.search.service import search_foods, suggest_foods
from api.core.exceptions import ValidationError
from api.core.exceptions import to_http_exception

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
def search(
    q: str = "",
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search foods."""
    if not q.strip():
        raise to_http_exception(ValidationError("Query parameter q is required"))
    if len(q.strip()) < 2:
        return {"results": [], "count": 0, "not_found": True, "message": "Type at least 2 characters"}

    results = search_foods(db, q.strip(), limit, user.has_diabetes)

    return {
        "results": results,
        "count": len(results),
        "not_found": len(results) == 0,
        "message": "Item not found" if len(results) == 0 else None,
    }


@router.get("/suggest")
def suggest(
    q: str = "",
    limit: int = 10,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Autocomplete suggestions for food names."""
    if not q.strip():
        return {"results": [], "count": 0}
    results = suggest_foods(db, q.strip(), limit, user.has_diabetes)
    return {"results": results, "count": len(results)}
