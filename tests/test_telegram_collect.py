import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import telegram_collect as tc

TODAY = int(dt.datetime.now(dt.timezone.utc).timestamp())
APPROVED = {"work_editor": {"username": "work_editor", "authorized": True}}

def post(text, id=10, username="work_editor"):
    return {"message_id": id, "date": TODAY, "chat": {"username": username, "type": "channel"}, "text": text}

class TelegramTests(unittest.TestCase):
    def test_approval_is_explicit(self):
        config = {"approved_channels": [{"username": "work_editor", "authorized": True},
                     {"username": "textodromo", "authorized": False}]}
        self.assertEqual(list(tc.approved_channels(config)), ["work_editor"])
    def test_parse_content_job_from_ru(self):
        text = "UX-редактор\nКомпания: Альфа\nФормат: удалённо из России\nЗарплата: 160 000 ₽\nЗадачи: писать тексты интерфейсов. Требования: опыт от 2 лет."
        job = tc.parse_post(post(text), APPROVED)
        self.assertIsNotNone(job)
        self.assertEqual(job["company"], "Альфа")
        self.assertEqual(job["salary"], "160 000 ₽")
        self.assertEqual(job["sources"][0]["url"], "https://t.me/work_editor/10")
    def test_reject_foreign_and_unknown_geography(self):
        self.assertIsNone(tc.parse_post(post("Редактор\nКомпания: А\nТребования: удалённая работа по всему миру, вакансии в Казахстане."), APPROVED))
        self.assertIsNone(tc.parse_post(post("SMM-менеджер\nКомпания: Б\nТребования: 2 года опыта, удалённо. Отправьте портфолио."), APPROVED))
    def test_ignore_unauthorized(self):
        self.assertIsNone(tc.parse_post(post("Редактор\nКомпания: А\nМосква\nТребования: писать тексты.", username="random_channel"), APPROVED))
    def test_update_same_post(self):
        original = tc.parse_post(post("Редактор\nКомпания: А\nМосква\nТребования: писать тексты."), APPROVED)
        updated, stats = tc.sync_posts([original], [
            {"update_id": 1, "edited_channel_post": post("Редактор\nВакансия закрыта\nМосква\nТребования: писать тексты.")}
        ], APPROVED)
        self.assertEqual(updated, [])
        self.assertEqual(stats["removed"], 1)
    def test_deduplicate_post(self):
        p = post("Редактор\nКомпания: А\nМосква\nТребования: писать тексты.")
        results, _ = tc.sync_posts([], [{"update_id": 1, "channel_post": p}, {"update_id": 2, "channel_post": p}], APPROVED)
        self.assertEqual(len(results), 1)
    def test_salary_is_only_from_stated_compensation(self):
        p = post("Редактор\nКомпания: А\nМосква\nНаш курс стоит 50 000 ₽. Требования: опыт.")
        job = tc.parse_post(p, APPROVED)
        self.assertEqual(job["salary"], "")

if __name__ == "__main__":
    unittest.main()
