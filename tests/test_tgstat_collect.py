import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import tgstat_collect as t
NOW=int(dt.datetime.now(dt.timezone.utc).timestamp())

def item(text, link="t.me/work_editor/152", date=NOW, deleted=0):
    return {"text":text,"link":link,"date":date,"is_deleted":deleted}

TEXT="Редактор\nКомпания: Пример\nМосква\nЗадачи: писать статьи и редактировать.\nТребования: опыт 2 года.\nЗарплата: 140 000 ₽"

class TGStatTests(unittest.TestCase):
    def test_valid_post(self):
        j=t.parse_item(item(TEXT))
        self.assertIsNotNone(j)
        self.assertEqual(j["company"],"Пример")
        self.assertEqual(j["salary"],"140 000 ₽")
        self.assertEqual(j["sources"][0]["url"],"https://t.me/work_editor/152")

    def test_reject_no_location(self):
        self.assertIsNone(t.parse_item(item("Редактор\nКомпания: Пример\nТребования: опыт 2 года.\nУдалённая работа.")))

    def test_reject_foreign(self):
        self.assertIsNone(t.parse_item(item(TEXT.replace("Москва","Казахстан"))))

    def test_reject_deleted(self):
        self.assertIsNone(t.parse_item(item(TEXT,deleted=1)))

    def test_reject_old(self):
        self.assertIsNone(t.parse_item(item(TEXT,date=NOW-20*86400)))

    def test_reject_invalid_link(self):
        self.assertIsNone(t.parse_item(item(TEXT,link="https://example.com/post")))

    def test_reject_stray_price(self):
        raw="Редактор\nКомпания: Пример\nМосква\nТребования: опыт 3 года. Курс стоит 160 000 ₽, а работать нужно с текстами."
        j=t.parse_item(item(raw))
        self.assertIsNotNone(j)
        self.assertEqual(j["salary"],"")

    def test_dedup_by_link(self):
        j=t.parse_item(item(TEXT))
        self.assertEqual(len(t.merge_tgstat([j],[j])),1)

    def test_search_uses_max_five_requests(self):
        batch=t.batch_queries({"mode":"search","max_requests_per_run":5,"search_terms":["редактор","UX-редактор","копирайтер","SMM","контент","руководитель"]},{})
        self.assertEqual(len(batch),5)
        self.assertTrue(all(x[0]=="posts/search" for x in batch))

    def test_channels_cursor(self):
        state={"cursor":2}
        config={"mode":"channels","max_requests_per_run":2,"channel_usernames":["a1234","b1234","c1234","d1234"]}
        batch=t.batch_queries(config,state)
        self.assertEqual([x[1]["channelId"] for x in batch],["@c1234","@d1234"])
        self.assertEqual(state["cursor"],0)

if __name__ == "__main__":
    unittest.main()
