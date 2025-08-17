# 🔐 Настройка Google Sheets API для бота

## 📋 **Обзор**
Этот модуль позволяет боту взаимодействовать с Google Sheets через сервисный аккаунт Google Cloud.

## 🚀 **Быстрая настройка (рекомендуется)**

### **1. Создание сервисного аккаунта Google Cloud**

#### **Шаг 1: Создание проекта**
1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Запомните **Project ID**

#### **Шаг 2: Включение API**
1. В меню слева выберите "APIs & Services" → "Library"
2. Найдите "Google Sheets API"
3. Нажмите "Enable"

#### **Шаг 3: Создание сервисного аккаунта**
1. Перейдите в "APIs & Services" → "Credentials"
2. Нажмите "Create Credentials" → "Service Account"
3. Заполните:
   - **Name**: `cardbot-sheets-api`
   - **Description**: `Service account for CardBot Google Sheets integration`
4. Нажмите "Create and Continue"
5. Пропустите роли (нажмите "Continue")
6. Нажмите "Done"

#### **Шаг 4: Создание ключа**
1. В списке сервисных аккаунтов нажмите на созданный
2. Перейдите на вкладку "Keys"
3. Нажмите "Add Key" → "Create new key"
4. Выберите "JSON"
5. Скачайте файл `service-account.json`

### **2. Настройка доступа к таблице**

#### **Шаг 1: Создание Google таблицы**
1. Перейдите на [Google Sheets](https://sheets.google.com/)
2. Создайте новую таблицу или используйте существующую
3. Скопируйте **ID таблицы** из URL:
   ```
   https://docs.google.com/spreadsheets/d/1RoWWv9BgiwlSu9H-KJNsFItQxlUVhG1WMbyB0eFxzYM/edit
   ID: 1RoWWv9BgiwlSu9H-KJNsFItQxlUVhG1WMbyB0eFxzYM
   ```

#### **Шаг 2: Предоставление доступа**
1. В таблице нажмите "Share" (Поделиться)
2. Добавьте email сервисного аккаунта из `service-account.json`:
   ```
   cardbot-sheets-api@your-project.iam.gserviceaccount.com
   ```
3. Дайте права "Editor" (Редактор)
4. Нажмите "Send"

### **3. Настройка переменных окружения в Amvera**

#### **Вариант A: Base64 кодирование (РЕКОМЕНДУЕТСЯ для безопасности)**

1. **Закодируйте JSON в base64:**
   ```bash
   # В терминале (Linux/Mac)
   cat service-account.json | base64
   
   # В Windows PowerShell
   [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes((Get-Content service-account.json -Raw)))
   ```

2. **Создайте переменную в Amvera:**
   - **Название:** `GOOGLE_SERVICE_ACCOUNT_BASE64`
   - **Значение:** `eyJ0eXBlIjoic2VydmljZV9hY2NvdW50Ii...` (весь base64 код)

#### **Вариант B: Обычный JSON (не рекомендуется)**
- **Название:** `GOOGLE_SERVICE_ACCOUNT`
- **Значение:** `{"type":"service_account","project_id":"..."}`

#### **Вариант C: Путь к файлу (не рекомендуется)**
- **Название:** `GOOGLE_SERVICE_ACCOUNT_PATH`
- **Значение:** `/app/service-account.json`

## 🧪 **Тестирование**

### **Команды для проверки:**

1. **Тест подключения:**
   ```
   /sheets_test
   ```

2. **Информация о таблице:**
   ```
   /sheets_info 1RoWWv9BgiwlSu9H-KJNsFItQxlUVhG1WMbyB0eFxzYM
   ```

3. **Чтение данных:**
   ```
   /sheets_read 1RoWWv9BgiwlSu9H-KJNsFItQxlUVhG1WMbyB0eFxzYM marketplaces
   ```

## 🔒 **Безопасность**

### **Рекомендации:**
- ✅ Используйте **base64 кодирование** для переменных окружения
- ✅ Ограничьте права сервисного аккаунта только необходимыми таблицами
- ✅ Регулярно обновляйте ключи сервисного аккаунта
- ❌ НЕ добавляйте `service-account.json` в git репозиторий
- ❌ НЕ используйте переменные с открытым JSON в production

### **Минимальные права:**
- Google Sheets API: чтение/запись
- Google Drive API: доступ к конкретным файлам
- НЕ давайте права на весь Google Drive

## 🚨 **Устранение неполадок**

### **Ошибка: "Переменные не настроены"**
- Проверьте, что переменная `GOOGLE_SERVICE_ACCOUNT_BASE64` создана в Amvera
- Убедитесь, что base64 код корректный

### **Ошибка: "Access denied"**
- Проверьте, что сервисный аккаунт добавлен в таблицу
- Убедитесь, что права доступа установлены как "Editor"

### **Ошибка: "Invalid JSON"**
- Проверьте, что base64 код декодируется корректно
- Убедитесь, что исходный JSON файл валидный

## 📚 **Дополнительные ресурсы**

- [Google Cloud Console](https://console.cloud.google.com/)
- [Google Sheets API Documentation](https://developers.google.com/sheets/api)
- [Service Account Best Practices](https://cloud.google.com/iam/docs/service-accounts-best-practices)
