import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import collect
class ParagraphTests(unittest.TestCase):
    def test_preserve_paragraphs(self):
        raw="Что делать:\n• Писать тексты\n• Редактировать\n\nЧто уметь:\nFigma"
        job=collect.make_job("UX-редактор","Компания","https://example.com/1",raw,"Москва")
        self.assertIsNotNone(job)
        self.assertIn("\n• Писать",job["description"])
        self.assertIn("\n\nЧто уметь",job["description"])
    def test_html_jobposting_keeps_bullets(self):
        obj={"title":"Редактор","description":"<p>Задачи:</p><ul><li>Писать</li><li>Проверять</li></ul>","jobLocation":{"address":{"addressLocality":"Москва"}}}
        j=collect.structured_job(obj,"https://example.com","Компания")
        self.assertIsNotNone(j)
        self.assertIn("\nПисать\n",j["description"])
if __name__=="__main__":unittest.main()
