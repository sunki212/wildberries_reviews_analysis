from python.db_connection import get_db_connection
from sentence_transformers import SentenceTransformer
import numpy as np
import torch

# Конфигурация
MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'  # 384-мерные эмбеддинги
BATCH_SIZE = 100  # Размер батча для обработки

def generate_all_embeddings():
    """Обрабатывает все необработанные отзывы за один запуск"""
    model = SentenceTransformer(MODEL_NAME)
    total_processed = 0

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Сначала получим общее количество отзывов для обработки
        cursor.execute("""
            SELECT COUNT(*) 
            FROM reviews r
            LEFT JOIN embeddings e ON r.review_id = e.review_id
            WHERE e.review_id IS NULL
        """)
        total_to_process = cursor.fetchone()[0]
        
        if total_to_process == 0:
            print("Нет новых отзывов для обработки")
            return 0

        print(f"Начало обработки {total_to_process} отзывов...")

        # Основной цикл обработки батчами
        while True:
            # Получаем батч необработанных отзывов
            cursor.execute("""
                SELECT r.review_id, r.text 
                FROM reviews r
                WHERE NOT EXISTS(
                    SELECT 1 FROM embeddings e
                    WHERE e.review_id = r.review_id
                )
                ORDER BY r.review_id
                LIMIT %s
            """, (BATCH_SIZE,))
            
            batch = cursor.fetchall()
            if not batch:
                break  # Все обработано

            review_ids, texts = zip(*batch)
            
            # Генерация эмбеддингов для батча
            embeddings = model.encode(texts, convert_to_tensor=True)
            embeddings = embeddings.cpu().numpy()

            # Вставляем все эмбеддинги батча одной транзакцией
            try:
                cursor.executemany(
                    "INSERT INTO embeddings (review_id, vector) VALUES (%s, %s)",
                    [(rid, emb.tolist()) for rid, emb in zip(review_ids, embeddings)]
                )
                conn.commit()
                processed = len(batch)
                total_processed += processed
                print(f"Обработан батч: {processed} записей | Всего: {total_processed}/{total_to_process}")
            except Exception as e:
                conn.rollback()
                print(f"Ошибка при обработке батча: {str(e)}")
                raise

    print(f"Готово! Обработано отзывов: {total_processed}")
    return total_processed

if __name__ == "__main__":
    generate_all_embeddings()