create extension if not exists vector;
select null::vector

 --1. Таблица товаров
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    has_sizes BOOLEAN NOT NULL,
    color VARCHAR(100)
);

-- 2. Таблица пользователей
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    reviewer_name TEXT NOT null UNIQUE,
    gender_token CHAR(3) NOT NULL CHECK (gender_token IN ('<М>', '<Ж>', '<Н>')) -- M: Мужской, F: Женский, U: Неизвестно
);

-- 3. Таблица отзывов
CREATE TABLE reviews (
    review_id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    is_obscene BOOLEAN NOT NULL,
    matching_size VARCHAR(10) NOT NULL CHECK (matching_size IN ('ok', 'smaller', 'bigger')),
    mark SMALLINT NOT NULL CHECK (mark BETWEEN 1 AND 5),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Анализ тональности
CREATE TABLE sentiment_analysis (
    sentiment_id SERIAL PRIMARY KEY,
    review_id INTEGER NOT NULL REFERENCES reviews(review_id) ON DELETE CASCADE,
    score FLOAT NOT NULL CHECK (score BETWEEN -1.0 AND 1.0), -- Диапазон тональности
    label VARCHAR(10) NOT NULL CHECK (label IN ('positive', 'neutral', 'negative'))
);

-- 5. Ключевые фразы
CREATE TABLE key_phrases (
    phrase_id SERIAL PRIMARY KEY,
    review_id INTEGER NOT NULL REFERENCES reviews(review_id) ON DELETE CASCADE,
    phrase TEXT NOT NULL
);

-- 6. Логи NLP
CREATE TABLE nlp_logs (
    log_id SERIAL PRIMARY KEY,
    review_id INTEGER REFERENCES reviews(review_id) ON DELETE SET NULL,
    task_type VARCHAR(20) NOT NULL CHECK (task_type IN ('sentiment', 'key_phrases', 'embedding')),
    status VARCHAR(10) NOT NULL CHECK (status IN ('started', 'completed', 'failed')),
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. Эмбеддинги
CREATE TABLE embeddings (
    embedding_id SERIAL PRIMARY KEY,
    review_id INTEGER NOT NULL UNIQUE REFERENCES reviews(review_id) ON DELETE CASCADE,
    vector VECTOR(384) NOT NULL -- Вектор размерностью 384
);

CREATE EXTENSION IF NOT EXISTS pg_trgm;
-- Индексы для оптимизации
CREATE INDEX idx_products_name ON products(name);
CREATE INDEX idx_reviews_mark ON reviews(mark);
CREATE INDEX idx_reviews_created ON reviews(created_at);
CREATE INDEX idx_sentiment_label ON sentiment_analysis(label);
CREATE INDEX idx_key_phrases ON key_phrases USING GIN (phrase gin_trgm_ops); -- Для текстового поиска
CREATE INDEX idx_embeddings_vector ON embeddings USING hnsw (vector vector_cosine_ops); -- Для косинусной близости

-- Триггер для автоматического обновления updated_at в отзывах
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_reviews_modtime
BEFORE UPDATE ON reviews
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();
