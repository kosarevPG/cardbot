# 🔧 Настройка Google Sheets API

## 📋 Предварительные требования

1. **Google Cloud Project** - создайте проект в [Google Cloud Console](https://console.cloud.google.com/)
2. **Google Sheets API** - включите API в проекте
3. **Сервисный аккаунт** - создайте аккаунт для программного доступа

## 🚀 Пошаговая настройка

### 1. Создание Google Cloud Project

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Запомните **Project ID** - он понадобится позже

### 2. Включение Google Sheets API

1. В меню слева выберите **APIs & Services** → **Library**
2. Найдите **Google Sheets API**
3. Нажмите **Enable**

### 3. Создание сервисного аккаунта

1. В меню слева выберите **APIs & Services** → **Credentials**
2. Нажмите **Create Credentials** → **Service Account**
3. Заполните форму:
   - **Name**: `marathon-bot-sheets-reader` (или любое другое)
   - **Description**: `Service account for reading Google Sheets`
4. Нажмите **Create and Continue**
5. Пропустите шаги с ролями (нажмите **Continue**)
6. Нажмите **Done**

### 4. Создание ключа сервисного аккаунта

1. В списке сервисных аккаунтов найдите созданный
2. Нажмите на email аккаунта
3. Перейдите на вкладку **Keys**
4. Нажмите **Add Key** → **Create new key**
5. Выберите **JSON** формат
6. Нажмите **Create**
7. Файл автоматически скачается

### 5. Настройка доступа к таблице

1. Откройте Google таблицу, к которой нужен доступ
2. Нажмите **Share** (кнопка "Настройки доступа")
3. Добавьте email сервисного аккаунта (найдите в скачанном JSON файле)
4. Дайте права **Editor** или **Viewer** (в зависимости от потребностей)

## 🔑 Настройка в Amvera

### Вариант 1: Переменная окружения (рекомендуется)

1. В панели Amvera перейдите в **Environment Variables**
2. Добавьте переменную:
   - **Name**: `GOOGLE_SERVICE_ACCOUNT`
   - **Value**: содержимое JSON файла (в одну строку)

### Вариант 2: Файл

1. Загрузите JSON файл в проект
2. Добавьте переменную:
   - **Name**: `GOOGLE_SERVICE_ACCOUNT_PATH`
   - **Value**: путь к файлу (например, `/app/service-account.json`)

## 📊 Использование команд

После настройки вы сможете использовать команды:

- `/sheets_test` - тест подключения
- `/sheets_info SPREADSHEET_ID` - информация о таблице
- `/sheets_read SPREADSHEET_ID [SHEET_NAME]` - чтение данных

## 🔍 Получение ID таблицы

ID таблицы находится в URL:
```
https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
```

## ⚠️ Важные замечания

1. **Безопасность**: никогда не публикуйте JSON файл сервисного аккаунта
2. **Права доступа**: давайте минимально необходимые права
3. **Квоты**: Google Sheets API имеет ограничения на количество запросов
4. **Мониторинг**: следите за использованием API в Google Cloud Console

## 🆘 Устранение неполадок

### Ошибка "Service account not found"
- Проверьте правильность JSON в переменной окружения
- Убедитесь, что сервисный аккаунт создан

### Ошибка "Access denied"
- Проверьте права доступа к таблице
- Убедитесь, что email сервисного аккаунта добавлен в доступ

### Ошибка "API not enabled"
- Проверьте, что Google Sheets API включен в проекте
- Убедитесь, что проект выбран правильно

## 📚 Дополнительные ресурсы

- [Google Sheets API Documentation](https://developers.google.com/sheets/api)
- [Google Cloud Console](https://console.cloud.google.com/)
- [Service Account Best Practices](https://cloud.google.com/iam/docs/service-accounts)
