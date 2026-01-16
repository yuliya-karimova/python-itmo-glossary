"""
Скрипт для импорта данных из CSV файлов в базу данных
"""
import csv
import sys
from pathlib import Path
from sqlalchemy.orm import Session

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models import Term, Link, SessionLocal, init_db


def import_terms(csv_path: str, db: Session):
    """Импорт терминов из CSV"""
    # Определяем типы узлов
    def get_node_type(term_name: str) -> str:
        if term_name == 'Подход к разработке интерфейса':
            return 'root'
        elif term_name in ['Классическая разработка UI', 'Backend-Driven UI']:
            return 'approach'
        else:
            return 'term'
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Проверяем, существует ли термин
            existing = db.query(Term).filter(Term.term == row['term']).first()
            node_type = get_node_type(row['term'])
            if not existing:
                term = Term(term=row['term'], definition=row['definition'], node_type=node_type)
                db.add(term)
                print(f"Добавлен термин: {row['term']} (тип: {node_type})")
            else:
                # Обновляем определение и тип, если они изменились
                updated = False
                if existing.definition != row['definition']:
                    existing.definition = row['definition']
                    updated = True
                    print(f"Обновлено определение термина: {row['term']}")
                if existing.node_type != node_type:
                    existing.node_type = node_type
                    updated = True
                    print(f"Обновлен тип термина: {row['term']} -> {node_type}")
                if not updated:
                    print(f"Термин уже актуален: {row['term']}")
    db.commit()


def import_links(csv_path: str, db: Session):
    """Импорт связей из CSV"""
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Находим термины
            source_term = db.query(Term).filter(Term.term == row['source']).first()
            target_term = db.query(Term).filter(Term.term == row['target']).first()
            
            if not source_term:
                print(f"Предупреждение: исходный термин '{row['source']}' не найден")
                continue
            if not target_term:
                print(f"Предупреждение: целевой термин '{row['target']}' не найден")
                continue
            
            # Проверяем, существует ли связь
            existing = db.query(Link).filter(
                Link.source_id == source_term.id,
                Link.target_id == target_term.id,
                Link.relation == row['relation']
            ).first()
            
            if not existing:
                link = Link(
                    source_id=source_term.id,
                    target_id=target_term.id,
                    relation=row['relation']
                )
                db.add(link)
                print(f"Добавлена связь: {row['source']} -> {row['target']} ({row['relation']})")
            else:
                print(f"Связь уже существует: {row['source']} -> {row['target']}")
    db.commit()


def main():
    """Основная функция импорта"""
    # Инициализация БД
    init_db()
    
    # Получаем пути к CSV файлам
    base_dir = Path(__file__).parent.parent
    terms_csv = base_dir / "terms.csv"
    links_csv = base_dir / "links.csv"
    
    db = SessionLocal()
    try:
        print("Импорт терминов...")
        if terms_csv.exists():
            import_terms(str(terms_csv), db)
        else:
            print(f"Файл {terms_csv} не найден")
        
        print("\nИмпорт связей...")
        if links_csv.exists():
            import_links(str(links_csv), db)
        else:
            print(f"Файл {links_csv} не найден")
        
        print("\nИмпорт завершен!")
    except Exception as e:
        print(f"Ошибка при импорте: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()

