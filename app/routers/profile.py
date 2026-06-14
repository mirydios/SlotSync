from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path

from app.database import get_db
from app.models.user import User
from app.models.booking import PublicLink

router = APIRouter(tags=["Profile"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

@router.get("/u/{username}", response_class=HTMLResponse)
def public_profile(request: Request, username: str, db: Session = Depends(get_db)):
    """Public profile page listing all active booking links for a user."""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    active_links = (
        db.query(PublicLink)
        .filter(
            PublicLink.user_id == user.id,
            PublicLink.is_active == True,
        )
        .all()
    )

    return templates.TemplateResponse("profile_page.html", {
        "request": request,
        "owner": user,
        "links": active_links,
    })
