"""
Модели базы данных для глоссария
"""
import os
from sqlalchemy import Column, Integer, String, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


class Term(Base):
    """Модель термина"""
    __tablename__ = "terms"
    
    id = Column(Integer, primary_key=True, index=True)
    term = Column(String, unique=True, index=True, nullable=False)
    definition = Column(String, nullable=False)
    node_type = Column(String, default='term', nullable=False)  # Тип узла: 'root', 'approach', 'term'
    
    # Связи
    source_links = relationship("Link", foreign_keys="Link.source_id", back_populates="source_term")
    target_links = relationship("Link", foreign_keys="Link.target_id", back_populates="target_term")


class Link(Base):
    """Модель связи между терминами"""
    __tablename__ = "links"
    
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("terms.id"), nullable=False)
    target_id = Column(Integer, ForeignKey("terms.id"), nullable=False)
    relation = Column(String, nullable=False)
    
    # Связи
    source_term = relationship("Term", foreign_keys=[source_id], back_populates="source_links")
    target_term = relationship("Term", foreign_keys=[target_id], back_populates="target_links")


# Настройка базы данных
DB_PATH = os.getenv("DB_PATH", "./data/glossary.db")
os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Инициализация базы данных - создание таблиц и миграции"""
    Base.metadata.create_all(bind=engine)
    
    # Миграция: добавление колонки node_type, если её нет
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('terms')]
    
    if 'node_type' not in columns:
        with engine.connect() as conn:
            conn.execute(text('ALTER TABLE terms ADD COLUMN node_type VARCHAR DEFAULT "term"'))
            conn.commit()
        print("Миграция: добавлена колонка node_type")


def get_db():
    """Получение сессии базы данных"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

