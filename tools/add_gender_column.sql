-- Добавление столбца gender в таблицу users
-- Выполнить вручную в SQLite браузере или через Python

-- Проверяем, существует ли уже столбец gender
-- Если нет, добавляем его
ALTER TABLE users ADD COLUMN gender TEXT DEFAULT 'neutral';

-- Комментарий: 
-- gender может иметь значения: 'male', 'female', 'neutral'
-- По умолчанию устанавливается 'neutral'

