from python.db_connection import get_db_connection
from natasha import (
    Doc,
    Segmenter,
    NewsEmbedding,
    NewsMorphTagger,
    MorphVocab
)
import re
import logging
from string import punctuation
from sklearn.feature_extraction.text import TfidfVectorizer
from collections import defaultdict
import numpy as np

# Инициализация Natasha
segmenter = Segmenter()
emb = NewsEmbedding()
morph_tagger = NewsMorphTagger(emb)
morph_vocab = MorphVocab()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nlp_processor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def text_processing(text):
    """Обработка текста с расширенной проверкой"""
    if not text or not isinstance(text, str) or text.isspace():
        return ""
    
    text = text.lower().strip()
    text = re.sub(r'\d+', '', text)
    text = text.translate(str.maketrans('', '', punctuation))
    return text if text else ""

def analyze_sentiment_natasha(text):
    """Анализ тональности с Natasha"""
    if text is None:
        return 0.0, 'neutral'
    
    clean_text = text_processing(text)
    if not clean_text:
        return 0.0, 'neutral'
    
    try:
        doc = Doc(clean_text)
        doc.segment(segmenter)
        doc.tag_morph(morph_tagger)
    
        positive_phrases = {
            'отличный', 'прекрасный', 'рекомендую', 'доволен', 
            'качественный', 'хороший', 'супер', 'отлично', 'плюс'
        }
        negative_phrases = {
            'плохой', 'ужасный', 'разочарован', 'недостаток', 
            'брак', 'минус', 'недочет', 'недоволен', 'слабый'
        }
    
        pos_count = 0
        neg_count = 0
        
        for token in doc.tokens:
            if token.lemma is None:
                continue
            lemma = token.lemma.lower()
            if lemma in positive_phrases:
                pos_count += 1
            elif lemma in negative_phrases:
                neg_count += 1
    
        total = pos_count + neg_count
        if total == 0:
            return 0.0, 'neutral'
        
        score = (pos_count - neg_count) / total
        if score > 0.2:
            return min(score, 1.0), 'positive'
        elif score < -0.2:
            return max(score, -1.0), 'negative'
        else:
            return score, 'neutral'
            
    except Exception as e:
        logger.error(f"Ошибка сентимент-анализа: {str(e)}", exc_info=True)
        return 0.0, 'neutral'

def extract_keywords_tfidf(texts, top_n=5):
    """Извлечение ключевых слов с помощью TF-IDF"""
    try:
        # Создаем TF-IDF векторaйзер
        vectorizer = TfidfVectorizer(max_features=1000)
        tfidf_matrix = vectorizer.fit_transform(texts)
        
        # Получаем слова и их веса
        feature_names = vectorizer.get_feature_names_out()
        tfidf_scores = np.asarray(tfidf_matrix.mean(axis=0)).ravel()
        
        # Сортируем слова по их важности
        sorted_indices = tfidf_scores.argsort()[::-1]
        keywords = [feature_names[i] for i in sorted_indices[:top_n]]
        
        return keywords
    except Exception as e:
        logger.error(f"Ошибка в TF-IDF анализе: {str(e)}", exc_info=True)
        return []

def process_reviews():
    """Основная функция обработки отзывов"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            try:
                # Получаем все отзывы для анализа
                cursor.execute("""
                    SELECT r.review_id, r.text 
                    FROM reviews r
                    WHERE r.text IS NOT NULL
                    AND r.text != ''
                    AND NOT r.text ~ '^\\s*$'
                    AND NOT EXISTS (
                        SELECT 1 FROM nlp_logs l 
                        WHERE l.review_id = r.review_id 
                        AND l.task_type IN ('sentiment', 'key_phrases')
                        AND l.status = 'completed'
                    )
                    ORDER BY r.review_id
                    FOR UPDATE SKIP LOCKED
                """)
                
                reviews = cursor.fetchall()
                
                if not reviews:
                    logger.info("Нет новых отзывов для обработки.")
                    return 0
                
                # Подготовка данных для TF-IDF
                review_ids, texts = zip(*reviews)
                texts = [text_processing(text) for text in texts]
                
                # Извлекаем ключевые слова для всех отзывов
                all_keywords = extract_keywords_tfidf(texts)
                
                # Создаем словарь для хранения ключевых слов по отзывам
                review_keywords = defaultdict(list)
                for keyword in all_keywords:
                    for i, text in enumerate(texts):
                        if keyword in text:
                            review_keywords[review_ids[i]].append(keyword)
                
                processed = 0
                for review_id, text in reviews:
                    try:
                        # Обработка каждого отзыва
                        logger.info(f"Обработка отзыва {review_id}")
                        
                        # Анализ тональности
                        sentiment_score, sentiment_label = analyze_sentiment_natasha(text)
                        
                        # Удаляем старые записи перед вставкой новых
                        cursor.execute(
                            "DELETE FROM sentiment_analysis WHERE review_id = %s",
                            (review_id,)
                        )
                        cursor.execute(
                            "INSERT INTO sentiment_analysis (review_id, score, label) VALUES (%s, %s, %s)",
                            (review_id, sentiment_score, sentiment_label)
                        )
                        
                        # Ключевые слова для текущего отзыва
                        keywords = review_keywords.get(review_id, [])[:5]
                        
                        # Удаляем старые ключевые фразы
                        cursor.execute(
                            "DELETE FROM key_phrases WHERE review_id = %s",
                            (review_id,)
                        )
                        
                        # Вставляем новые ключевые фразы
                        for keyword in keywords:
                            cursor.execute(
                                "INSERT INTO key_phrases (review_id, phrase) VALUES (%s, %s)",
                                (review_id, keyword)
                            )
                        
                        # Логируем успешное завершение
                        cursor.execute(
                            "INSERT INTO nlp_logs (review_id, task_type, status) VALUES (%s, 'sentiment', 'completed')",
                            (review_id,)
                        )
                        cursor.execute(
                            "INSERT INTO nlp_logs (review_id, task_type, status) VALUES (%s, 'key_phrases', 'completed')",
                            (review_id,)
                        )
                        
                        conn.commit()
                        processed += 1
                        
                    except Exception as e:
                        conn.rollback()
                        logger.error(f"Ошибка в отзыве {review_id}: {str(e)}", exc_info=True)
                        cursor.execute(
                            "INSERT INTO nlp_logs (review_id, task_type, status, message) VALUES (%s, 'sentiment', 'failed', %s)",
                            (review_id, str(e)[:200])
                        )
                        cursor.execute(
                            "INSERT INTO nlp_logs (review_id, task_type, status, message) VALUES (%s, 'key_phrases', 'failed', %s)",
                            (review_id, str(e)[:200])
                        )
                        conn.commit()
                
                logger.info(f"Успешно обработано {processed} из {len(reviews)} отзывов")
                return processed
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Ошибка при обработке отзывов: {str(e)}", exc_info=True)
                return 0

if __name__ == "__main__":
    logger.info("Запуск NLP процессора")
    total_processed = 0
    
    # Обрабатываем все отзывы за один проход
    processed = process_reviews()
    total_processed += processed
    
    logger.info(f"Обработка завершена. Итого обработано: {total_processed} отзывов")