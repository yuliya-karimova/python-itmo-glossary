"""
Глоссарий терминов по теме "Исследование Backend-Driven UI для быстрой доставки изменений интерфейса конечному пользователю"
FastAPI приложение с SQLite базой данных
"""
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from typing import Optional, List
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime
import os

# Настройка базы данных
# Создаем директорию для БД, если её нет
os.makedirs("data", exist_ok=True)
SQLALCHEMY_DATABASE_URL = "sqlite:///./data/glossary.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Модель базы данных для терминов
class TermDB(Base):
    __tablename__ = "terms"
    
    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=False)
    source = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи для семантического графа
    related_terms = relationship(
        "TermRelation",
        foreign_keys="TermRelation.term_id",
        back_populates="term"
    )

# Модель для связей между терминами (семантический граф)
class TermRelation(Base):
    __tablename__ = "term_relations"
    
    id = Column(Integer, primary_key=True, index=True)
    term_id = Column(Integer, ForeignKey("terms.id"), nullable=False)
    related_term_id = Column(Integer, ForeignKey("terms.id"), nullable=False)
    relation_type = Column(String, default="related")  # related, synonym, antonym, etc.
    
    term = relationship("TermDB", foreign_keys=[term_id], back_populates="related_terms")
    related_term = relationship("TermDB", foreign_keys=[related_term_id])

# Создание таблиц при старте
def create_tables():
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Ошибка при создании таблиц: {e}")

create_tables()

# Pydantic модели для валидации
class TermCreate(BaseModel):
    keyword: str = Field(..., min_length=1, description="Ключевое слово термина")
    description: str = Field(..., min_length=1, description="Описание термина")
    source: Optional[str] = Field(None, description="Источник определения")
    related_terms: Optional[List[int]] = Field(default=[], description="ID связанных терминов")

class TermUpdate(BaseModel):
    keyword: Optional[str] = Field(None, min_length=1, description="Ключевое слово термина")
    description: Optional[str] = Field(None, min_length=1, description="Описание термина")
    source: Optional[str] = Field(None, description="Источник определения")
    related_terms: Optional[List[int]] = Field(default=None, description="ID связанных терминов")

class TermResponse(BaseModel):
    id: int
    keyword: str
    description: str
    source: Optional[str]
    created_at: datetime
    updated_at: datetime
    related_terms: List[dict] = []
    
    class Config:
        from_attributes = True

# Создание приложения FastAPI
app = FastAPI(
    title="Глоссарий Backend-Driven UI",
    description="API для управления глоссарием терминов по теме Backend-Driven UI",
    version="1.0.0"
)

# Настройка CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение статических файлов для фронтенда
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Зависимость для получения сессии БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Функция для получения связанных терминов
def get_related_terms_data(db: Session, term_id: int) -> List[dict]:
    relations = db.query(TermRelation).filter(TermRelation.term_id == term_id).all()
    result = []
    for rel in relations:
        related_term = db.query(TermDB).filter(TermDB.id == rel.related_term_id).first()
        if related_term:
            result.append({
                "id": related_term.id,
                "keyword": related_term.keyword,
                "relation_type": rel.relation_type
            })
    return result

# Корневой эндпойнт
@app.get("/")
async def root():
    return {
        "message": "Глоссарий Backend-Driven UI API",
        "docs": "/docs",
        "redoc": "/redoc",
        "frontend": "/static/index.html"
    }

# Получение списка всех терминов
@app.get("/terms", response_model=List[TermResponse])
async def get_all_terms(
    skip: int = Query(0, ge=0, description="Количество пропущенных записей"),
    limit: int = Query(100, ge=1, le=1000, description="Максимальное количество записей"),
    db: Session = Depends(get_db)
):
    """Получить список всех терминов с пагинацией"""
    terms = db.query(TermDB).offset(skip).limit(limit).all()
    result = []
    for term in terms:
        term_dict = {
            "id": term.id,
            "keyword": term.keyword,
            "description": term.description,
            "source": term.source,
            "created_at": term.created_at,
            "updated_at": term.updated_at,
            "related_terms": get_related_terms_data(db, term.id)
        }
        result.append(term_dict)
    return result

# Получение информации о конкретном термине по ключевому слову
@app.get("/terms/search", response_model=List[TermResponse])
async def search_term(
    keyword: str = Query(..., min_length=1, description="Ключевое слово для поиска"),
    db: Session = Depends(get_db)
):
    """Поиск термина по ключевому слову (частичное совпадение)"""
    terms = db.query(TermDB).filter(TermDB.keyword.contains(keyword)).all()
    if not terms:
        raise HTTPException(status_code=404, detail=f"Термин с ключевым словом '{keyword}' не найден")
    
    result = []
    for term in terms:
        term_dict = {
            "id": term.id,
            "keyword": term.keyword,
            "description": term.description,
            "source": term.source,
            "created_at": term.created_at,
            "updated_at": term.updated_at,
            "related_terms": get_related_terms_data(db, term.id)
        }
        result.append(term_dict)
    return result

# Получение термина по ID
@app.get("/terms/{term_id}", response_model=TermResponse)
async def get_term_by_id(term_id: int, db: Session = Depends(get_db)):
    """Получить информацию о термине по ID"""
    term = db.query(TermDB).filter(TermDB.id == term_id).first()
    if not term:
        raise HTTPException(status_code=404, detail=f"Термин с ID {term_id} не найден")
    
    return {
        "id": term.id,
        "keyword": term.keyword,
        "description": term.description,
        "source": term.source,
        "created_at": term.created_at,
        "updated_at": term.updated_at,
        "related_terms": get_related_terms_data(db, term.id)
    }

# Добавление нового термина
@app.post("/terms", response_model=TermResponse, status_code=201)
async def create_term(term: TermCreate, db: Session = Depends(get_db)):
    """Добавить новый термин в глоссарий"""
    # Проверка на существование термина с таким ключевым словом
    existing_term = db.query(TermDB).filter(TermDB.keyword == term.keyword).first()
    if existing_term:
        raise HTTPException(status_code=400, detail=f"Термин с ключевым словом '{term.keyword}' уже существует")
    
    # Создание нового термина
    db_term = TermDB(
        keyword=term.keyword,
        description=term.description,
        source=term.source
    )
    db.add(db_term)
    db.commit()
    db.refresh(db_term)
    
    # Добавление связей с другими терминами
    if term.related_terms:
        for related_id in term.related_terms:
            # Проверка существования связанного термина
            related_term = db.query(TermDB).filter(TermDB.id == related_id).first()
            if related_term and related_id != db_term.id:
                relation = TermRelation(
                    term_id=db_term.id,
                    related_term_id=related_id,
                    relation_type="related"
                )
                db.add(relation)
    
    db.commit()
    db.refresh(db_term)
    
    return {
        "id": db_term.id,
        "keyword": db_term.keyword,
        "description": db_term.description,
        "source": db_term.source,
        "created_at": db_term.created_at,
        "updated_at": db_term.updated_at,
        "related_terms": get_related_terms_data(db, db_term.id)
    }

# Обновление существующего термина
@app.put("/terms/{term_id}", response_model=TermResponse)
async def update_term(term_id: int, term_update: TermUpdate, db: Session = Depends(get_db)):
    """Обновить существующий термин"""
    db_term = db.query(TermDB).filter(TermDB.id == term_id).first()
    if not db_term:
        raise HTTPException(status_code=404, detail=f"Термин с ID {term_id} не найден")
    
    # Обновление полей
    if term_update.keyword is not None:
        # Проверка на уникальность ключевого слова
        existing = db.query(TermDB).filter(TermDB.keyword == term_update.keyword, TermDB.id != term_id).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Термин с ключевым словом '{term_update.keyword}' уже существует")
        db_term.keyword = term_update.keyword
    
    if term_update.description is not None:
        db_term.description = term_update.description
    
    if term_update.source is not None:
        db_term.source = term_update.source
    
    db_term.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_term)
    
    # Обновление связей
    if term_update.related_terms is not None:
        # Удаление старых связей
        db.query(TermRelation).filter(TermRelation.term_id == term_id).delete()
        # Добавление новых связей
        for related_id in term_update.related_terms:
            related_term = db.query(TermDB).filter(TermDB.id == related_id).first()
            if related_term and related_id != term_id:
                relation = TermRelation(
                    term_id=term_id,
                    related_term_id=related_id,
                    relation_type="related"
                )
                db.add(relation)
        db.commit()
    
    return {
        "id": db_term.id,
        "keyword": db_term.keyword,
        "description": db_term.description,
        "source": db_term.source,
        "created_at": db_term.created_at,
        "updated_at": db_term.updated_at,
        "related_terms": get_related_terms_data(db, db_term.id)
    }

# Удаление термина
@app.delete("/terms/{term_id}")
async def delete_term(term_id: int, db: Session = Depends(get_db)):
    """Удалить термин из глоссария"""
    db_term = db.query(TermDB).filter(TermDB.id == term_id).first()
    if not db_term:
        raise HTTPException(status_code=404, detail=f"Термин с ID {term_id} не найден")
    
    # Удаление всех связей
    db.query(TermRelation).filter(
        (TermRelation.term_id == term_id) | (TermRelation.related_term_id == term_id)
    ).delete()
    
    # Удаление термина
    db.delete(db_term)
    db.commit()
    
    return {"message": f"Термин '{db_term.keyword}' успешно удален"}

# Получение данных для визуализации графа
@app.get("/terms/graph/data")
async def get_graph_data(db: Session = Depends(get_db)):
    """Получить данные для визуализации семантического графа"""
    terms = db.query(TermDB).all()
    relations = db.query(TermRelation).all()
    
    nodes = []
    for term in terms:
        nodes.append({
            "id": term.id,
            "label": term.keyword,
            "description": term.description,
            "source": term.source
        })
    
    edges = []
    for rel in relations:
        edges.append({
            "from": rel.term_id,
            "to": rel.related_term_id,
            "type": rel.relation_type
        })
    
    return {
        "nodes": nodes,
        "edges": edges
    }

# Инициализация начальных данных
def init_db():
    """Инициализация базы данных начальными данными"""
    try:
        # Убеждаемся, что таблицы созданы
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Ошибка при создании таблиц в init_db: {e}")
        return
    
    db = SessionLocal()
    try:
        # Проверка, есть ли уже данные
        if db.query(TermDB).count() > 0:
            return
        
        # Начальные термины по теме Backend-Driven UI
        initial_terms = [
            {
                "keyword": "Backend-Driven UI",
                "description": "Подход к разработке интерфейсов, при котором структура и конфигурация UI определяются на бэкенде и доставляются клиентскому приложению динамически.",
                "source": "Современные практики разработки мобильных приложений"
            },
            {
                "keyword": "Server-Driven UI",
                "description": "Архитектурный паттерн, при котором сервер определяет структуру пользовательского интерфейса, а клиент рендерит его динамически.",
                "source": "Mobile App Architecture"
            },
            {
                "keyword": "JSON Schema",
                "description": "Стандарт для описания структуры JSON-данных, используемый для валидации и генерации UI компонентов.",
                "source": "JSON Schema Specification"
            },
            {
                "keyword": "Over-the-Air Update",
                "description": "Технология обновления приложения или его компонентов без публикации новой версии в магазинах приложений.",
                "source": "Mobile Development Practices"
            },
            {
                "keyword": "Feature Flag",
                "description": "Механизм включения и отключения функций приложения без изменения кода, управляемый сервером.",
                "source": "Continuous Delivery Practices"
            },
            {
                "keyword": "A/B Testing",
                "description": "Методология тестирования, при которой разные варианты интерфейса показываются разным группам пользователей для оценки эффективности.",
                "source": "User Experience Research"
            },
            {
                "keyword": "Dynamic UI",
                "description": "Пользовательский интерфейс, структура и содержимое которого могут изменяться во время выполнения приложения.",
                "source": "UI/UX Design Principles"
            },
            {
                "keyword": "API Gateway",
                "description": "Единая точка входа для всех клиентских запросов, которая маршрутизирует запросы к соответствующим микросервисам.",
                "source": "Microservices Architecture"
            },
            {
                "keyword": "Content Delivery Network",
                "description": "Распределенная сеть серверов, обеспечивающая быструю доставку контента пользователям в зависимости от их географического расположения.",
                "source": "Web Infrastructure"
            },
            {
                "keyword": "Hot Reload",
                "description": "Технология обновления интерфейса приложения без его перезапуска, позволяющая видеть изменения в реальном времени.",
                "source": "Development Tools"
            }
        ]
        
        # Добавление терминов
        term_objects = []
        for term_data in initial_terms:
            term = TermDB(**term_data)
            term_objects.append(term)
            db.add(term)
        
        db.commit()
        
        # Добавление связей между терминами
        # Backend-Driven UI связан с Server-Driven UI, Dynamic UI, Over-the-Air Update
        relations = [
            (1, 2, "related"),  # Backend-Driven UI -> Server-Driven UI
            (1, 7, "related"),  # Backend-Driven UI -> Dynamic UI
            (1, 4, "related"),  # Backend-Driven UI -> Over-the-Air Update
            (2, 7, "related"),  # Server-Driven UI -> Dynamic UI
            (3, 1, "related"),  # JSON Schema -> Backend-Driven UI
            (4, 5, "related"),  # Over-the-Air Update -> Feature Flag
            (5, 6, "related"),  # Feature Flag -> A/B Testing
        ]
        
        for term_id, related_id, rel_type in relations:
            relation = TermRelation(
                term_id=term_id,
                related_term_id=related_id,
                relation_type=rel_type
            )
            db.add(relation)
        
        db.commit()
        print("База данных инициализирована начальными данными")
    except Exception as e:
        print(f"Ошибка при инициализации БД: {e}")
        db.rollback()
    finally:
        db.close()

# Инициализация при старте приложения
@app.on_event("startup")
async def startup_event():
    init_db()
