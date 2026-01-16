"""
FastAPI приложение для глоссария терминов Backend-Driven UI
"""
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List

from app.models import Term, Link, get_db, init_db
from app.schemas import (
    TermCreate, TermUpdate, TermResponse,
    LinkCreate, LinkResponse,
    GraphResponse, GraphNode, GraphEdge
)

# Инициализация приложения
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

# Подключение статических файлов
app.mount("/static", StaticFiles(directory="static"), name="static")

# Инициализация БД при старте
@app.on_event("startup")
async def startup_event():
    init_db()
    # Импорт данных из CSV при первом запуске (если база пустая)
    from app.models import SessionLocal, Term
    db = SessionLocal()
    try:
        term_count = db.query(Term).count()
        if term_count == 0:
            from app.import_data import main as import_main
            import_main()
    finally:
        db.close()


# ========== API для терминов ==========

@app.get("/api/terms", response_model=List[TermResponse], tags=["Термины"])
async def get_terms(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Получить список всех терминов"""
    terms = db.query(Term).offset(skip).limit(limit).all()
    return terms


@app.get("/api/terms/{term_id}", response_model=TermResponse, tags=["Термины"])
async def get_term(term_id: int, db: Session = Depends(get_db)):
    """Получить информацию о конкретном термине по ID"""
    term = db.query(Term).filter(Term.id == term_id).first()
    if not term:
        raise HTTPException(status_code=404, detail="Термин не найден")
    return term


@app.get("/api/terms/search/{keyword}", response_model=List[TermResponse], tags=["Термины"])
async def search_term(keyword: str, db: Session = Depends(get_db)):
    """Поиск терминов по ключевому слову"""
    terms = db.query(Term).filter(
        Term.term.contains(keyword) | Term.definition.contains(keyword)
    ).all()
    return terms


@app.post("/api/terms", response_model=TermResponse, status_code=status.HTTP_201_CREATED, tags=["Термины"])
async def create_term(term_data: TermCreate, db: Session = Depends(get_db)):
    """Добавить новый термин"""
    # Проверка на существование
    existing = db.query(Term).filter(Term.term == term_data.term).first()
    if existing:
        raise HTTPException(status_code=400, detail="Термин уже существует")
    
    db_term = Term(term=term_data.term, definition=term_data.definition)
    db.add(db_term)
    db.commit()
    db.refresh(db_term)
    return db_term


@app.put("/api/terms/{term_id}", response_model=TermResponse, tags=["Термины"])
async def update_term(term_id: int, term_data: TermUpdate, db: Session = Depends(get_db)):
    """Обновить существующий термин"""
    term = db.query(Term).filter(Term.id == term_id).first()
    if not term:
        raise HTTPException(status_code=404, detail="Термин не найден")
    
    if term_data.term is not None:
        # Проверка на дубликат при изменении названия
        existing = db.query(Term).filter(Term.term == term_data.term, Term.id != term_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Термин с таким названием уже существует")
        term.term = term_data.term
    
    if term_data.definition is not None:
        term.definition = term_data.definition
    
    db.commit()
    db.refresh(term)
    return term


@app.delete("/api/terms/{term_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Термины"])
async def delete_term(term_id: int, db: Session = Depends(get_db)):
    """Удалить термин"""
    term = db.query(Term).filter(Term.id == term_id).first()
    if not term:
        raise HTTPException(status_code=404, detail="Термин не найден")
    
    # Удаляем связанные связи
    db.query(Link).filter(
        (Link.source_id == term_id) | (Link.target_id == term_id)
    ).delete()
    
    db.delete(term)
    db.commit()
    return None


# ========== API для связей ==========

@app.get("/api/links", response_model=List[LinkResponse], tags=["Связи"])
async def get_links(db: Session = Depends(get_db)):
    """Получить все связи между терминами"""
    links = db.query(Link).all()
    result = []
    for link in links:
        source_term = db.query(Term).filter(Term.id == link.source_id).first()
        target_term = db.query(Term).filter(Term.id == link.target_id).first()
        result.append(LinkResponse(
            id=link.id,
            source=source_term.term,
            target=target_term.term,
            relation=link.relation
        ))
    return result


@app.post("/api/links", response_model=LinkResponse, status_code=status.HTTP_201_CREATED, tags=["Связи"])
async def create_link(link_data: LinkCreate, db: Session = Depends(get_db)):
    """Создать связь между терминами"""
    # Находим термины
    source_term = db.query(Term).filter(Term.term == link_data.source).first()
    target_term = db.query(Term).filter(Term.term == link_data.target).first()
    
    if not source_term:
        raise HTTPException(status_code=404, detail=f"Исходный термин '{link_data.source}' не найден")
    if not target_term:
        raise HTTPException(status_code=404, detail=f"Целевой термин '{link_data.target}' не найден")
    
    # Проверка на дубликат
    existing = db.query(Link).filter(
        Link.source_id == source_term.id,
        Link.target_id == target_term.id,
        Link.relation == link_data.relation
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Такая связь уже существует")
    
    db_link = Link(
        source_id=source_term.id,
        target_id=target_term.id,
        relation=link_data.relation
    )
    db.add(db_link)
    db.commit()
    db.refresh(db_link)
    
    return LinkResponse(
        id=db_link.id,
        source=source_term.term,
        target=target_term.term,
        relation=db_link.relation
    )


@app.delete("/api/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Связи"])
async def delete_link(link_id: int, db: Session = Depends(get_db)):
    """Удалить связь"""
    link = db.query(Link).filter(Link.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Связь не найдена")
    
    db.delete(link)
    db.commit()
    return None


# ========== API для графа ==========

@app.get("/api/graph", response_model=GraphResponse, tags=["Граф"])
async def get_graph(db: Session = Depends(get_db)):
    """Получить полный граф терминов для визуализации"""
    terms = db.query(Term).all()
    links = db.query(Link).all()
    
    # Создаем узлы
    nodes = [
        GraphNode(
            id=str(term.id),
            label=term.term,
            definition=term.definition,
            node_type=term.node_type or 'term'
        )
        for term in terms
    ]
    
    # Создаем ребра
    edges = [
        GraphEdge(
            source=str(link.source_id),
            target=str(link.target_id),
            relation=link.relation
        )
        for link in links
    ]
    
    return GraphResponse(nodes=nodes, edges=edges)


# ========== Утилиты ==========

@app.post("/api/import", tags=["Утилиты"])
async def import_data():
    """Импорт данных из CSV файлов (ручной запуск)"""
    try:
        from app.import_data import main as import_main
        import_main()
        return {"message": "Данные успешно импортированы"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка импорта: {str(e)}")


# ========== Фронтенд ==========

@app.get("/", response_class=HTMLResponse, tags=["Фронтенд"])
async def read_root():
    """Главная страница с визуализацией графа"""
    template_path = Path(__file__).parent / "templates" / "index.html"
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()

