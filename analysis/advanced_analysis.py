import psycopg2
from python.db_connection import get_db_connection
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def analyze_emotional_categories():
    """Анализ эмоциональной окраски по категориям товаров"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.name, s.label, COUNT(*) as count
            FROM products p
            JOIN reviews r ON p.product_id = r.product_id
            JOIN sentiment_analysis s ON r.review_id = s.review_id
            GROUP BY p.name, s.label
            ORDER BY p.name, count DESC
        """)
        return cursor.fetchall()

def detect_fake_reviews(threshold=0.9, max_batches=100, batch_size=100, show_progress=True):
    """Обнаружение фальшивых отзывов с ограничением по количеству батчей"""
    similar_pairs = []
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        if show_progress:
            print(f"Обработка первых {max_batches} батчей по {batch_size} отзывов...")
        
        for batch_num in range(max_batches):
            offset = batch_num * batch_size
            
            # Получаем батч отзывов
            cursor.execute("""
                SELECT review_id, vector 
                FROM embeddings 
                ORDER BY review_id 
                LIMIT %s OFFSET %s
            """, (batch_size, offset))
            
            batch = cursor.fetchall()
            if not batch:
                break  # если данные закончились
                
            # Преобразуем векторы
            batch_ids = [e[0] for e in batch]
            batch_vectors = []
            
            for e in batch:
                vector_str = e[1].strip('[]')
                vector = np.fromstring(vector_str, sep=',', dtype=np.float32)
                batch_vectors.append(vector)
            
            batch_vectors = np.array(batch_vectors)
            
            # Вычисляем схожесть внутри батча
            similarity_matrix = cosine_similarity(batch_vectors)
            
            # Находим схожие пары
            for i in range(len(similarity_matrix)):
                for j in range(i+1, len(similarity_matrix[i])):
                    if similarity_matrix[i][j] > threshold:
                        similar_pairs.append((
                            batch_ids[i], 
                            batch_ids[j], 
                            float(similarity_matrix[i][j])
                        ))
            
            if show_progress:
                print(f"Обработан батч {batch_num + 1}/{max_batches} | Найдено пар: {len(similar_pairs)}", end='\r')
    
    if show_progress:
        print(f"\nОбработка завершена. Всего найдено {len(similar_pairs)} подозрительных пар.")
    
    return similar_pairs

if __name__ == "__main__":
    print("Анализ эмоциональной окраски по категориям:")
    print(analyze_emotional_categories())
    
    print("Поиск фальшивых отзывов (первые 100 батчей):")
    fake_pairs = detect_fake_reviews(threshold=0.85)
    
    # Выводим первые 10 результатов для примера
    print("\nПримеры найденных пар:")
    for pair in fake_pairs[:10]:
        print(f"Отзывы {pair[0]} и {pair[1]} - схожесть {pair[2]:.2f}")