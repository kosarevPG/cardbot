# modules/texts/__init__.py
# Система управления текстами бота

from .gender_utils import personalize_text, get_user_info_for_text, get_personalized_text
from .learning import LEARNING_TEXTS
from .cards import CARDS_TEXTS
from .marketplace import MARKETPLACE_TEXTS
from .errors import ERROR_TEXTS
from .common import COMMON_TEXTS

__all__ = [
    'personalize_text',
    'get_user_info_for_text',
    'get_personalized_text',
    'LEARNING_TEXTS',
    'CARDS_TEXTS', 
    'MARKETPLACE_TEXTS',
    'ERROR_TEXTS',
    'COMMON_TEXTS'
]
