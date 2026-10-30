"""
Регрессионный тест разового анонса TopPsyGame и постов с картинкой.

Запуск:  python tests/test_announcement_post.py
Код возврата 0 — все проверки пройдены, 1 — есть падения.

Работает на временной базе, созданной с нуля, — боевые данные не нужны.
Ничего никуда не отправляется: бот подменён заглушкой.

Что защищаем:
  * текст анонса совпадает с согласованным дословно — расхождение значит, что
    копирайт правили мимо согласования;
  * обе ссылки несут все четыре UTM-метки, а якорь «#platform» стоит ПОСЛЕ
    query-строки: иначе параметры станут частью фрагмента и до аналитики
    не доедут, причём молча;
  * в ссылках нет Telegram ID и прочих персональных данных;
  * пост с картинкой проходит по лимиту подписи (1024), а не сообщения (4096),
    и слишком длинный отклоняется при создании, а не в середине рассылки;
  * картинка доезжает до отправки: пост с media_file_id уходит фотографией
    с подписью, без неё — обычным сообщением;
  * предпросмотр уходит только автору команды и не пишет строк в журнал
    рассылки, то есть не попадает в статистику.
"""
import asyncio
import os
import re
import sys
import tempfile
from urllib.parse import parse_qs, urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from database.db import Database
from modules.post_management import MEDIA_CAPTION_LIMIT, TEXT_LIMIT, PostManager
from modules.texts.announcement import (
    ANNOUNCEMENT_TITLE, announcement_text, app_url, site_url,
)

failures = []


def check(name, actual, expected):
    if actual == expected:
        print(f"  OK   {name}")
    else:
        print(f"  FAIL {name}: ожидалось {expected}, получено {actual}")
        failures.append(name)


# Согласованный текст анонса. Лежит здесь отдельной копией намеренно: тест
# должен падать, если копирайт поправили в modules/texts/announcement.py, —
# текст согласован с заказчиком, и тихо разойтись с ним он не должен.
APPROVED = """🃏 У нас новость — появилась TopPsyGame!

Мы запустили онлайн-платформу для работы с метафорическими картами и трансформационными играми.

Теперь можно проводить МАК-сессии и игры прямо в браузере: выбирать инструменты, создавать игровые комнаты и приглашать участников.

✨ Посмотрите, что получилось!

Узнать о платформе:
toppsygame.ru/#platform

Перейти в приложение:
online.toppsygame.ru"""


class FakeBot:
    """Запоминает отправленное вместо обращения к Telegram."""

    def __init__(self):
        self.photos = []
        self.messages = []

    async def send_photo(self, chat_id, photo, caption=None, **kwargs):
        self.photos.append({"chat_id": chat_id, "photo": photo, "caption": caption})

    async def send_message(self, chat_id, text, **kwargs):
        self.messages.append({"chat_id": chat_id, "text": text})


class FakeLoggerService:
    def __init__(self):
        self.actions = []

    async def log_action(self, user_id, action, details=None):
        self.actions.append((user_id, action, details))


def visible_text(html: str) -> str:
    """То, что увидит получатель: Telegram считает длину подписи по нему."""
    return re.sub(r"<[^>]+>", "", html)


def test_texts():
    print("Текст анонса:")
    rendered = announcement_text()
    check("видимый текст совпадает с согласованным", visible_text(rendered), APPROVED)
    check("ссылка на лендинг в тексте", site_url() in rendered, True)
    check("ссылка на приложение в тексте", app_url() in rendered, True)

    print("Ссылки с метками:")
    for name, url, host, content in (
        ("лендинг", site_url(), "toppsygame.ru", "site"),
        ("приложение", app_url(), "online.toppsygame.ru", "app"),
    ):
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        check(f"{name}: хост", parsed.hostname, host)
        check(f"{name}: utm_source", params.get("utm_source"), ["cardbot"])
        check(f"{name}: utm_medium", params.get("utm_medium"), ["telegram"])
        check(f"{name}: utm_campaign", params.get("utm_campaign"), ["platform_announcement"])
        check(f"{name}: utm_content", params.get("utm_content"), [content])
        # Персональных данных в ссылке быть не должно: она уходит во внешний
        # сервис и оседает в его логах.
        check(f"{name}: нет лишних параметров", sorted(params),
              ["utm_campaign", "utm_content", "utm_medium", "utm_source"])

    # Якорь обязан стоять последним. '/#platform?utm_source=...' означало бы,
    # что весь query — часть фрагмента, и аналитика его не увидит.
    parsed_site = urlparse(site_url())
    check("якорь раздела платформы", parsed_site.fragment, "platform")
    check("query идёт до якоря", site_url().index("?") < site_url().index("#"), True)
    check("у приложения якоря нет", urlparse(app_url()).fragment, "")

    print("Недопустимая метка:")
    from modules.texts import announcement
    try:
        announcement._with_utm(announcement.SITE_URL, "telegram_id_123")
        check("закрытый список utm_content", "ошибки нет", "ValueError")
    except ValueError:
        check("закрытый список utm_content", "ValueError", "ValueError")


def test_limits(manager):
    print("Лимиты длины:")
    long_text = "x" * (MEDIA_CAPTION_LIMIT + 1)

    without = manager.validate_post_data("Заголовок", long_text, has_media=False)
    check("без картинки 1025 символов проходит", without["valid"], True)

    with_media = manager.validate_post_data("Заголовок", long_text, has_media=True)
    check("с картинкой 1025 символов отклоняются", with_media["valid"], False)
    check("в ошибке назван лимит подписи",
          str(MEDIA_CAPTION_LIMIT) in " ".join(with_media["errors"]), True)

    fits = manager.validate_post_data("Заголовок", "x" * MEDIA_CAPTION_LIMIT, has_media=True)
    check("ровно 1024 с картинкой проходят", fits["valid"], True)

    too_long = manager.validate_post_data("Заголовок", "x" * (TEXT_LIMIT + 1), has_media=False)
    check("без картинки 4097 символов отклоняются", too_long["valid"], False)

    print("Реальный анонс:")
    real = manager.validate_post_data(ANNOUNCEMENT_TITLE, announcement_text(), has_media=True)
    check("анонс с картинкой проходит по лимиту", real["valid"], True)
    check("видимый текст короче лимита подписи",
          len(visible_text(announcement_text())) <= MEDIA_CAPTION_LIMIT, True)


def test_media_roundtrip(db, manager, bot):
    print("Картинка от создания до отправки:")
    post_id = manager.create_post(ANNOUNCEMENT_TITLE, announcement_text(), 6682555021, "FILE_ID_1")
    post = manager.get_post(post_id)
    check("media_file_id сохранился", post["media_file_id"], "FILE_ID_1")

    asyncio.run(manager.send_post_to_user(777, post))
    check("пост с картинкой ушёл фотографией", len(bot.photos), 1)
    check("обычным сообщением не дублируется", len(bot.messages), 0)
    check("получатель тот, кого просили", bot.photos[0]["chat_id"], 777)
    check("картинка та самая", bot.photos[0]["photo"], "FILE_ID_1")
    check("текст ушёл подписью", bot.photos[0]["caption"], announcement_text())

    print("Пост без картинки:")
    plain_id = manager.create_post("Без картинки", "Просто текст", 6682555021)
    plain = manager.get_post(plain_id)
    check("media_file_id пуст", plain["media_file_id"], None)
    asyncio.run(manager.send_post_to_user(777, plain))
    check("ушёл обычным сообщением", len(bot.messages), 1)
    check("фотографий не прибавилось", len(bot.photos), 1)

    print("Картинка, прикреплённая позже:")
    check("update_post вернул успех",
          manager.update_post(plain_id, media_file_id="FILE_ID_2"), True)
    check("картинка прикрепилась", manager.get_post(plain_id)["media_file_id"], "FILE_ID_2")
    # Текст поста при этом трогать нельзя: прикрепили картинку, а не переписали пост.
    check("текст не пострадал", manager.get_post(plain_id)["content"], "Просто текст")


def test_preview_is_not_a_mailing(db, manager, bot):
    print("Предпросмотр:")
    post_id = manager.create_post("Проверка", "Текст проверки", 6682555021, "FILE_ID_3")
    post = manager.get_post(post_id)

    before = db.conn.execute("SELECT COUNT(*) FROM mailing_logs").fetchone()[0]
    sent = asyncio.run(manager.send_post_to_user(6682555021, post))
    after = db.conn.execute("SELECT COUNT(*) FROM mailing_logs").fetchone()[0]

    check("предпросмотр доставлен", sent, True)
    check("получатель — только админ", bot.photos[-1]["chat_id"], 6682555021)
    # Без mailing_id строк в журнале не появляется: проверка не должна
    # притворяться рассылкой и портить её статистику.
    check("в журнал рассылок ничего не записано", after, before)
    check("рассылка не создана", len(manager.get_all_mailings(limit=10)), 0)


def main():
    path = os.path.join(tempfile.mkdtemp(), "bot.db")
    db = Database(path=path)
    bot = FakeBot()
    manager = PostManager(db, bot, FakeLoggerService())

    try:
        test_texts()
        test_limits(manager)
        test_media_roundtrip(db, manager, bot)
        test_preview_is_not_a_mailing(db, manager, bot)
    finally:
        db.close()

    print()
    if failures:
        print(f"ПАДЕНИЙ: {len(failures)} — {', '.join(failures)}")
        return 1
    print("Все проверки пройдены.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
