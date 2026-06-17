import asyncio
from sqlalchemy.orm import Session
from app.core.database import engine, SessionLocal, Base
from app.models.models import User


def init_db():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == 1).first()
        if not user:
            user = User(
                id=1,
                username="default_user",
                display_name="用户",
                persona_data={},
            )
            db.add(user)
            db.commit()
            print("初始化用户创建成功")
        else:
            print("用户已存在")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()