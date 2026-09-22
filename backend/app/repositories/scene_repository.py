from sqlalchemy.orm import Session

from app.models.scene import Scene


class SceneRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, scene_id: str) -> Scene | None:
        return self.session.get(Scene, scene_id)
