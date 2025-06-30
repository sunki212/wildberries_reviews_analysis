-- Функция для анализа тональности на основе словарного метода
CREATE OR REPLACE FUNCTION analyze_sentiment(review_text TEXT)
RETURNS TABLE(
    score FLOAT8,  -- Явно указываем double precision
    label VARCHAR(10)  -- Явно указываем varchar
) AS $$
DECLARE
    pos_count INTEGER;
    neg_count INTEGER;
    result_score FLOAT8;
    result_label VARCHAR(10);
BEGIN
    -- Считаем ключевые слова
    SELECT 
        COUNT(*) FILTER (WHERE word IN ('хороший', 'отличный', 'прекрасный')),
        COUNT(*) FILTER (WHERE word IN ('плохой', 'ужасный', 'кошмар'))
    INTO pos_count, neg_count
    FROM unnest(string_to_array(lower(review_text), ' ')) AS word;
    
    -- Определяем результат
    IF pos_count > neg_count THEN
        result_score := 0.5;
        result_label := 'positive';
    ELSIF pos_count < neg_count THEN
        result_score := -0.5;
        result_label := 'negative';
    ELSE
        result_score := 0.0;
        result_label := 'neutral';
    END IF;
    
    -- Возвращаем результат
    RETURN QUERY SELECT result_score::FLOAT8, result_label::VARCHAR(10);
END;
$$ LANGUAGE plpgsql;

-- Функция для поиска похожих отзывов по тексту (триграммы)
CREATE OR REPLACE FUNCTION find_similar_reviews(query_text TEXT)
RETURNS TABLE(
    review_id INTEGER,
    similarity DOUBLE PRECISION,
    product_name TEXT,
    review_text TEXT,
    rating INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        r.review_id::INTEGER,
        similarity(r.text, query_text)::DOUBLE PRECISION,
        p.name::TEXT,
        r.text::TEXT,
        r.mark::INTEGER
    FROM reviews r
    JOIN products p ON r.product_id = p.product_id
    WHERE similarity(r.text, query_text) > 0.3
    ORDER BY similarity DESC
    LIMIT 10;
END;
$$ LANGUAGE plpgsql;

-- Функция для поиска похожих отзывов по ключевым фразам (триграммы)
CREATE OR REPLACE FUNCTION find_similar_reviews_by_phrase(input_phrase_id INTEGER)
RETURNS TABLE(
    review_id INTEGER,
    similarity DOUBLE PRECISION,
    product_name TEXT,
    review_text TEXT,
    rating INTEGER
) AS $$
DECLARE
    query_phrase TEXT;
BEGIN
    -- Получаем текст фразы по её ID (используем переименованный параметр)
    SELECT phrase INTO query_phrase 
    FROM key_phrases 
    WHERE phrase_id = input_phrase_id;
    
    -- Если фраза не найдена, возвращаем пустой результат
    IF query_phrase IS NULL THEN
        RETURN;
    END IF;
    
    -- Ищем похожие отзывы по триграммному сходству
    RETURN QUERY
    SELECT 
        r.review_id::INTEGER,
        similarity(r.text, query_phrase)::DOUBLE PRECISION,
        p.name::TEXT,
        r.text::TEXT,
        r.mark::INTEGER
    FROM reviews r
    JOIN products p ON r.product_id = p.product_id
    WHERE similarity(r.text, query_phrase) > 0.3
    ORDER BY similarity DESC
    LIMIT 10;
END;
$$ LANGUAGE plpgsql;

-- Функция для поиска похожих отзывов по эмбеддингам
CREATE OR REPLACE FUNCTION find_similar_reviews_by_embedding(
    input_embedding_id INTEGER,
    similarity_threshold FLOAT8 DEFAULT 0.7,  -- Явно указываем double precision
    max_results INTEGER DEFAULT 10
)
RETURNS TABLE(
    review_id INTEGER,
    similarity FLOAT8,  -- Точное соответствие типов
    product_name TEXT,
    review_text TEXT,
    rating INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        r.review_id::INTEGER,
        (1 - (e2.vector <=> e1.vector))::FLOAT8 AS similarity,  -- Явное приведение типов
        p.name::TEXT,
        r.text::TEXT,
        r.mark::INTEGER
    FROM embeddings e1
    JOIN reviews r ON e1.review_id = r.review_id
    JOIN products p ON r.product_id = p.product_id
    JOIN embeddings e2 ON e2.embedding_id != e1.embedding_id
    WHERE e1.embedding_id = input_embedding_id
    AND (1 - (e2.vector <=> e1.vector))::FLOAT8 > similarity_threshold::FLOAT8
    ORDER BY similarity DESC
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

--Функция для выявления аномальных отзывов
CREATE OR REPLACE FUNCTION detect_anomal_reviews()
RETURNS TABLE(
    review_id INT, 
    mark SMALLINT,  -- Изменено с INT на SMALLINT
    sentiment_score FLOAT, 
    text TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        r.review_id::INT,
        r.mark::SMALLINT,
        s.score::FLOAT,
        r.text::TEXT
    FROM reviews r
    JOIN sentiment_analysis s ON r.review_id = s.review_id
    WHERE (r.mark >= 4 AND s.score < -0.3) OR (r.mark <= 2 AND s.score > 0.3);
END;
$$ LANGUAGE plpgsql;