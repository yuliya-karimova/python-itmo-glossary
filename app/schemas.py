"""
Pydantic схемы для валидации данных
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class TermBase(BaseModel):
    """Базовая схема термина"""
    term: str = Field(..., description="Название термина")
    definition: str = Field(..., description="Определение термина")
    node_type: Optional[str] = Field('term', description="Тип узла: root, approach, term")


class TermCreate(TermBase):
    """Схема для создания термина"""
    pass


class TermUpdate(BaseModel):
    """Схема для обновления термина"""
    term: Optional[str] = Field(None, description="Название термина")
    definition: Optional[str] = Field(None, description="Определение термина")
    node_type: Optional[str] = Field(None, description="Тип узла: root, approach, term")


class TermResponse(TermBase):
    """Схема ответа с термином"""
    id: int
    
    class Config:
        from_attributes = True


class LinkBase(BaseModel):
    """Базовая схема связи"""
    source: str = Field(..., description="Исходный термин")
    target: str = Field(..., description="Целевой термин")
    relation: str = Field(..., description="Тип связи")


class LinkCreate(LinkBase):
    """Схема для создания связи"""
    pass


class LinkResponse(LinkBase):
    """Схема ответа со связью"""
    id: int
    
    class Config:
        from_attributes = True


class GraphNode(BaseModel):
    """Узел графа для визуализации"""
    id: str
    label: str
    definition: str
    node_type: Optional[str] = 'term'  # Тип узла: root, approach, term


class GraphEdge(BaseModel):
    """Ребро графа для визуализации"""
    source: str
    target: str
    relation: str


class GraphResponse(BaseModel):
    """Полный граф для визуализации"""
    nodes: List[GraphNode]
    edges: List[GraphEdge]

