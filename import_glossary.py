"""
Скрипт для импорта глоссария из list.csv и definitions.txt в базу данных
"""
import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import Base, TermDB, TermRelation

# Настройка базы данных
import os
os.makedirs("data", exist_ok=True)
SQLALCHEMY_DATABASE_URL = "sqlite:///./data/glossary.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def load_definitions(filename):
    """Загружает определения терминов из файла"""
    definitions = {}
    current_term = None
    current_description = []
    
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Если строка не пустая и предыдущая была пустой или это первая строка
            if line and (i == 0 or (i > 0 and not lines[i-1].strip())):
                # Сохраняем предыдущий термин, если есть
                if current_term and current_description:
                    definitions[current_term] = '\n'.join(current_description).strip()
                    current_description = []
                
                # Новая строка - это название термина
                current_term = line
                i += 1
                
                # Пропускаем пустую строку после названия
                if i < len(lines) and not lines[i].strip():
                    i += 1
                
                # Читаем описание до следующей пустой строки или конца файла
                while i < len(lines):
                    desc_line = lines[i].strip()
                    if not desc_line:
                        break
                    current_description.append(desc_line)
                    i += 1
            else:
                i += 1
        
        # Добавляем последний термин
        if current_term and current_description:
            definitions[current_term] = '\n'.join(current_description).strip()
    
    return definitions

def parse_csv_file(filename):
    """Парсит CSV файл и извлекает термины и связи"""
    terms = {}  # словарь терминов: {term_name: description}
    relations = []  # список связей: [(term1, relation_type, term2)]
    
    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=';')
        for row in reader:
            if len(row) >= 3:
                term1 = row[0].strip()
                relation_type = row[1].strip()
                term2 = row[2].strip()
                
                # Добавляем термины в словарь
                if term1 not in terms:
                    terms[term1] = ""
                if term2 not in terms:
                    terms[term2] = ""
                
                # Добавляем связь
                relations.append((term1, relation_type, term2))
    
    return terms, relations

def import_to_database(terms, relations, definitions):
    """Импортирует термины и связи в базу данных"""
    db = SessionLocal()
    
    try:
        # Очищаем существующие данные
        print("Очистка существующих данных...")
        db.query(TermRelation).delete()
        db.query(TermDB).delete()
        db.commit()
        
        # Создаем термины с определениями
        print(f"Создание {len(terms)} терминов...")
        term_objects = {}
        for keyword in terms:
            description = definitions.get(keyword, f"Термин из глоссария: {keyword}")
            term = TermDB(
                keyword=keyword,
                description=description,
                source="Глоссарий Backend-Driven UI"
            )
            db.add(term)
            term_objects[keyword] = term
        
        db.commit()
        
        # Обновляем ID после коммита
        for keyword, term in term_objects.items():
            db.refresh(term)
            term_objects[keyword] = term
        
        # Создаем связи
        print(f"Создание {len(relations)} связей...")
        created_relations = 0
        skipped_relations = 0
        
        for term1_name, relation_type, term2_name in relations:
            if term1_name in term_objects and term2_name in term_objects:
                term1 = term_objects[term1_name]
                term2 = term_objects[term2_name]
                
                # Проверяем, нет ли уже такой связи
                existing = db.query(TermRelation).filter(
                    TermRelation.term_id == term1.id,
                    TermRelation.related_term_id == term2.id,
                    TermRelation.relation_type == relation_type
                ).first()
                
                if not existing:
                    relation = TermRelation(
                        term_id=term1.id,
                        related_term_id=term2.id,
                        relation_type=relation_type
                    )
                    db.add(relation)
                    created_relations += 1
                else:
                    skipped_relations += 1
            else:
                skipped_relations += 1
                print(f"Пропущена связь: {term1_name} -> {term2_name} (термин не найден)")
        
        db.commit()
        
        print(f"\nИмпорт завершен:")
        print(f"  - Терминов создано: {len(term_objects)}")
        print(f"  - Связей создано: {created_relations}")
        print(f"  - Связей пропущено: {skipped_relations}")
        
    except Exception as e:
        print(f"Ошибка при импорте: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("Загрузка определений из definitions.txt...")
    definitions = load_definitions("definitions.txt")
    print(f"Загружено определений: {len(definitions)}")
    
    print("\nПарсинг файла list.csv...")
    terms, relations = parse_csv_file("list.csv")
    
    print(f"Найдено:")
    print(f"  - Уникальных терминов: {len(terms)}")
    print(f"  - Связей: {len(relations)}")
    
    print("\nИмпорт в базу данных...")
    import_to_database(terms, relations, definitions)
    
    print("\nГотово! Запустите приложение для просмотра визуализации.")
