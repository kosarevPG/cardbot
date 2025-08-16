-- SQL-скрипт для мониторинга безопасности админ-панели
-- Проверяет попытки несанкционированного доступа

-- 1. Анализ попыток доступа к админ-функциям
SELECT 
    'ADMIN_ACCESS_ATTEMPTS' as check_type,
    user_id,
    username,
    name,
    action,
    timestamp,
    CASE 
        WHEN user_id IN (6682555021, 392141189, 239719200, 7494824111, 171507422, 138192985) 
        THEN 'LEGITIMATE_ADMIN' 
        ELSE 'UNAUTHORIZED_ACCESS' 
    END as access_type
FROM actions 
WHERE action LIKE 'admin_%'
    AND timestamp >= datetime('now', '-7 days')
ORDER BY timestamp DESC;

-- 2. Поиск пользователей, которые выполняли админские действия, но не являются админами
SELECT 
    'UNAUTHORIZED_ADMIN_ACTIONS' as check_type,
    user_id,
    username,
    name,
    COUNT(*) as action_count,
    GROUP_CONCAT(DISTINCT action) as actions_performed,
    MIN(timestamp) as first_attempt,
    MAX(timestamp) as last_attempt
FROM actions 
WHERE action LIKE 'admin_%'
    AND user_id NOT IN (6682555021, 392141189, 239719200, 7494824111, 171507422, 138192985)
    AND timestamp >= datetime('now', '-7 days')
GROUP BY user_id, username, name
ORDER BY action_count DESC;

-- 3. Проверка доступа к конфиденциальным данным
SELECT 
    'CONFIDENTIAL_DATA_ACCESS' as check_type,
    'user_requests' as data_type,
    COUNT(*) as total_requests,
    COUNT(DISTINCT user_id) as unique_users,
    MIN(timestamp) as earliest_access,
    MAX(timestamp) as latest_access
FROM user_requests 
WHERE timestamp >= datetime('now', '-7 days')
    AND user_id NOT IN (6682555021, 392141189, 239719200, 7494824111, 171507422, 138192985, 999999999);

-- 4. Анализ паттернов подозрительной активности
SELECT 
    'SUSPICIOUS_PATTERNS' as check_type,
    user_id,
    username,
    name,
    COUNT(*) as total_actions,
    COUNT(CASE WHEN action LIKE 'admin_%' THEN 1 END) as admin_actions,
    COUNT(CASE WHEN action NOT LIKE 'admin_%' THEN 1 END) as regular_actions,
    MIN(timestamp) as first_action,
    MAX(timestamp) as last_action
FROM actions 
WHERE user_id NOT IN (6682555021, 392141189, 239719200, 7494824111, 171507422, 138192985)
    AND timestamp >= datetime('now', '-7 days')
    AND (action LIKE 'admin_%' OR action IN ('card_flow_started', 'card_flow_completed'))
GROUP BY user_id, username, name
HAVING COUNT(CASE WHEN action LIKE 'admin_%' THEN 1 END) > 0
ORDER BY admin_actions DESC;

-- 5. Рекомендации по безопасности
SELECT 
    'SECURITY_RECOMMENDATIONS' as check_type,
    CASE 
        WHEN COUNT(*) > 0 THEN 'CRITICAL: Unauthorized admin access detected'
        ELSE 'OK: No unauthorized admin access'
    END as status,
    COUNT(*) as unauthorized_attempts,
    GROUP_CONCAT(DISTINCT user_id) as affected_users
FROM actions 
WHERE action LIKE 'admin_%'
    AND user_id NOT IN (6682555021, 392141189, 239719200, 7494824111, 171507422, 138192985)
    AND timestamp >= datetime('now', '-7 days'); 