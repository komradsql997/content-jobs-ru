import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import collect as c

class TestCollector(unittest.TestCase):
    def test_role(self):
        self.assertTrue(c.is_role("Старший UX-редактор"))
        self.assertFalse(c.is_role("Видео-редактор"))
    def test_location(self):
        self.assertIsNotNone(c.make_job("Главный редактор","Компания","https://example.ru/1","Задачи и требования","Москва"))
        self.assertIsNone(c.make_job("Главный редактор","Компания","https://example.ru/1","","London"))
        self.assertIsNone(c.make_job("Главный редактор","Компания","https://example.ru/1","",""))
    def test_canonical(self):
        self.assertEqual(c.canonical("https://test.ru/a/?utm_source=foo"),"https://test.ru/a")
    def test_merge(self):
        x=c.make_job("Редактор","Компания","https://example.ru/1","Опыт","Москва")
        y=c.make_job("Редактор","Компания","https://example.ru/2","Опыт","Москва")
        self.assertEqual(len(c.merge_jobs([x],[y])),1)
    def test_score(self):
        x=c.make_job("Редактор","Компания","https://example.ru/1","Задачи, требования и опыт. 150 000 ₽","Москва")
        self.assertLessEqual(x["score"],100)
        self.assertGreater(x["score"],0)

if __name__=="__main__":unittest.main()
