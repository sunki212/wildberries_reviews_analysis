# wildberries_reviews_analysis
Репозиторий анализа отзывов Wildberries методами NLP в рамках курса "Продвинутые запросы SQL"

# Структура проекта
wildberries_reviews_analysis/  
│  
├── database/  
│ ├── 01_tables.sql # создание таблиц и индексов  
│ └── 02_functions.sql # PL/pgSQL функции для анализа   
│  
├── python/  
│ ├── db_connection.py #подключение к PostgreSQL  
│ ├── data_loader.py # загрузка CSV в БД  
│ ├── nlp_processor.py # обработка текста (тональность, ключевые фразы)  
│ └── embedding_generator.py # генерация векторных представлений  
│  
├── analysis/  
│ ├── basic_analysis.sql # стандартные аналитические запросы  
│ └── advanced_analysis.py # Python-скрипты для сложной аналитики  
│  
├── config/  
│ ├── config.py  # данные подключения базы (в db_connection.py)
│ └── requirements.txt # зависимости Python  
│  
└── README.md
# Загрузка данных
Запустите скрипт  
```python data_loader.py```
# NLP-обработка
Анализ тональности и выделение ключевых фраз  
```python nlp_processor.py```
# Генерация эмбеддингов
Генерирует эмбеддинги для каждого отзыва (возможно прерывание команды с сохранением уже обработанных строк)  
```python embedding_generator.py```

# Проверка сгенерированных таблиц
```
SELECT * FROM key_phrases WHERE review_id = [ваш_id];
SELECT * FROM sentiment_analysis WHERE review_id = [ваш_id];
SELECT * FROM nlp_logs ORDER BY created_at DESC LIMIT 10;
```

