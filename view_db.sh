#!/bin/bash
# Скрипт для просмотра базы данных глоссария

DB_FILE="data/glossary.db"

echo "=== Таблицы в базе данных ==="
sqlite3 "$DB_FILE" ".tables"

echo -e "\n=== Количество терминов ==="
sqlite3 "$DB_FILE" "SELECT COUNT(*) as total FROM terms;"

echo -e "\n=== Список всех терминов ==="
sqlite3 "$DB_FILE" "SELECT id, keyword FROM terms;"

echo -e "\n=== Детали первого термина ==="
sqlite3 "$DB_FILE" "SELECT * FROM terms LIMIT 1;"

echo -e "\n=== Связи между терминами ==="
sqlite3 "$DB_FILE" "SELECT t1.keyword as term, t2.keyword as related_term, tr.relation_type 
                    FROM term_relations tr
                    JOIN terms t1 ON tr.term_id = t1.id
                    JOIN terms t2 ON tr.related_term_id = t2.id
                    LIMIT 5;"

echo -e "\n=== Интерактивный режим ==="
echo "Для интерактивного режима выполните: sqlite3 $DB_FILE"
echo "Полезные команды:"
echo "  .tables          - показать все таблицы"
echo "  .schema terms    - показать структуру таблицы terms"
echo "  SELECT * FROM terms;  - показать все термины"
echo "  .quit            - выйти"

