import csv
from python.db_connection import get_db_connection

def load_data_from_csv(file_path):
    """Загрузка данных из CSV в БД"""
    with get_db_connection() as conn, open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        cursor = conn.cursor()
        
        for row in reader:
            # Вставка продукта
            cursor.execute(
                """INSERT INTO products (name, description, has_sizes, color) 
                VALUES (%s, %s, %s, %s) RETURNING product_id""",
                (row['name'], row['description'], row['has_sizes'] == 'true', row['color'])
            )
            product_id = cursor.fetchone()[0]
            
            # Вставка пользователя
            cursor.execute(
                """INSERT INTO users (reviewer_name, gender_token) 
                VALUES (%s, %s) ON CONFLICT (reviewer_name) DO UPDATE 
                SET reviewer_name = EXCLUDED.reviewer_name 
                RETURNING user_id""",
                (row['reviewerName'], row['gender_token'])
            )
            user_id = cursor.fetchone()[0]
            
            # Вставка отзыва
            cursor.execute(
                """INSERT INTO reviews 
                (product_id, user_id, text, is_obscene, matching_size, mark) 
                VALUES (%s, %s, %s, %s, %s, %s)""",
                (product_id, user_id, row['text'], row['isObscene'] == 'true', 
                 row['matchingSize'], int(float(row['mark'])))
            )
        
        conn.commit()

if __name__ == "__main__":
    load_data_from_csv('prepared_data.csv')