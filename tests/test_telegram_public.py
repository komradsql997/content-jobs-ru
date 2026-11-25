import unittest,sys,datetime as dt
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import telegram_public as t
NOW=dt.datetime.now(dt.timezone.utc)
D=NOW.isoformat().replace("+00:00","Z")
def sample(content,url="work_editor/500"):
 return f'<div class="tgme_widget_message" data-post="{url}"><div class="tgme_widget_message_text">{content}</div><a class="tgme_widget_message_date"><time datetime="{D}"></time></a></div>'
class TelegramPublicTests(unittest.TestCase):
 def test_extract(self):
  html=sample("Редактор<br>Компания: Пример<br>Москва<br>Задачи: писать статьи<br>Зарплата: 150 000 ₽")
  j,d=t.parse_preview(html,"work_editor")
  self.assertEqual(len(j),1)
  self.assertEqual(j[0]["salary"],"150 000 ₽")
  self.assertEqual(j[0]["url"],"https://t.me/work_editor/500")
 def test_foreign(self):
  j,_=t.parse_preview(sample("Редактор<br>Компания: А<br>Казахстан<br>Опыт: 3 года"),"work_editor")
  self.assertEqual(len(j),0)
 def test_no_evidence_ru(self):
  j,_=t.parse_preview(sample("SMM-менеджер<br>Удаленная работа<br>Опыт: 3 года"),"work_editor")
  self.assertEqual(len(j),0)
 def test_wrong_channel(self):
  j,_=t.parse_preview(sample("Редактор<br>Москва<br>Требования: опыт",url="unrelated_channel/200"),"work_editor")
  self.assertEqual(len(j),0)
 def test_price_is_not_salary(self):
  j,_=t.parse_preview(sample("Копирайтер<br>Москва<br>Стоимость курса 150 000 ₽<br>Требования: опыт"),"work_editor")
  self.assertEqual(j[0]["salary"],"")
 def test_no_duplicates(self):
  block=sample("Редактор<br>Компания: А<br>Москва<br>Требования: опыт")
  j,_=t.parse_preview(block+block,"work_editor")
  self.assertEqual(len(j),1)

 def test_skip_resume(self):
  html=sample("Резюме: Контент-менеджер<br>Москва<br>Ищу работу редактором, опыт 2 года. Портфолио в профиле.")
  j,_=t.parse_preview(html,"work_editor")
  self.assertEqual(j,[])
 def test_skip_multi_post(self):
  html=sample("Подборка вакансий<br>Редактор в компании А<br>SMM в компании Б<br>Москва, условия разные.")
  j,_=t.parse_preview(html,"work_editor")
  self.assertEqual(j,[])
 def test_skip_unrelated_video_role(self):
  html=sample("ВИДЕОГРАФ<br>Москва<br>Участвовать в разработке контент-стратегии и предлагать идеи редактору.")
  j,_=t.parse_preview(html,"work_editor")
  self.assertEqual(j,[])
if __name__=="__main__":unittest.main()
