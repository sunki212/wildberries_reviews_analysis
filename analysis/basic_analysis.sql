-- Средний рейтинг по товарам
SELECT p.name, AVG(r.mark) as avg_rating, COUNT(r.review_id) as review_count
FROM products p
JOIN reviews r ON p.product_id = r.product_id
GROUP BY p.product_id
ORDER BY avg_rating desc
limit 10;

-- Распределение оценок
SELECT mark, COUNT(*) as count
FROM reviews
GROUP BY mark
ORDER BY mark;

-- Анализ тональности по категориям товаров
SELECT p.name, 
       s.label, 
       COUNT(*) as count,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY p.name), 2) as percentage
FROM products p
JOIN reviews r ON p.product_id = r.product_id
JOIN sentiment_analysis s ON r.review_id = s.review_id
GROUP BY p.name, s.label
ORDER BY p.name, count DESC;

-- Частота ключевых фраз в отзывах
SELECT phrase, COUNT(*) as frequency
FROM key_phrases
GROUP BY phrase
ORDER BY frequency DESC
LIMIT 20;