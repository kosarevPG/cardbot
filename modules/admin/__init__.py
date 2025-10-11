"""
Модуль админской панели.
Организован по функциональным блокам для удобства поддержки.
"""

# Импортируем все функции из подмодулей
from modules.admin.core import (
    make_admin_handler,
    make_admin_callback_handler,
    show_admin_main_menu
)

from modules.admin.dashboard import (
    show_admin_dashboard,
    show_admin_retention,
    show_admin_funnel,
    show_admin_value,
    show_admin_decks,
    show_admin_reflections,
    show_admin_logs
)

from modules.admin.users import (
    make_admin_user_profile_handler,
    show_admin_users,
    show_admin_users_list,
    show_admin_requests,
    show_admin_requests_full
)

from modules.admin.posts import (
    show_admin_posts,
    start_post_creation,
    show_posts_list,
    show_mailings_list,
    process_mailings_now
)

__all__ = [
    # Core
    'make_admin_handler',
    'make_admin_callback_handler',
    'show_admin_main_menu',
    
    # Dashboard
    'show_admin_dashboard',
    'show_admin_retention',
    'show_admin_funnel',
    'show_admin_value',
    'show_admin_decks',
    'show_admin_reflections',
    'show_admin_logs',
    
    # Users
    'make_admin_user_profile_handler',
    'show_admin_users',
    'show_admin_users_list',
    'show_admin_requests',
    'show_admin_requests_full',
    
    # Posts
    'show_admin_posts',
    'start_post_creation',
    'show_posts_list',
    'show_mailings_list',
    'process_mailings_now'
]

