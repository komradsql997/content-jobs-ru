import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import job_quality as q
import telegram_public as t

class QualityTests(unittest.TestCase):
 def test_netology_employer_and_role(self):
  text="Команда образовательной платформы Нетология ищет РЕДАКТОРА.\nЧем предстоит заниматься:\nПисать тексты"
  self.assertEqual(q.employer(text),"Нетология")
  self.assertEqual(t.job_title(text),"Редактор")
 def test_company_colon_and_platform(self):
  self.assertEqual(q.employer("Компания: Точка Банк\nРедактор"),"Точка Банк")
  self.assertEqual(q.employer("Название платформы:\nAdfinity.pro\nКопирайтер"),"Adfinity.pro")
 def test_promotional_footer_removed(self):
  text="Копирайтер\nМосква\nТребования: опыт\n➖\n➖\n📣\nРазместить вакансию\n/\nрекламу\n⚡️\nПолучать больше вакансий быстрее: «Работодром PRO»"
  actual=q.clean_post(text)
  self.assertNotIn("Работодром",actual)
  self.assertNotIn("Разместить",actual)
  self.assertNotIn("➖",actual)
  self.assertIn("Требования",actual)
 def test_canonical_title_is_not_accusative(self):
  self.assertEqual(q.clean_title("РЕДАКТОРА"),"Редактор")
  self.assertEqual(q.clean_title("Копирайтер-редактор, RTB, programmatic, монетизация |"),"Копирайтер-редактор, RTB, programmatic, монетизация")
 def test_stated_monthly_and_piece_rate(self):
  self.assertEqual(q.stated_pay("Зарплата: 120 000 ₽/мес"),"120 000 ₽")
  self.assertEqual(q.stated_pay("Уровень заработной платы\n2000 рублей (1 публикация)"),"2 000 ₽ за публикацию")
  self.assertEqual(q.stated_pay("Курс стоит 60 000 ₽"),"")
 def test_market_guesses_by_role_exclude_piece_rates(self):
  e={"title":"UX-редактор","category":"UX-тексты","level":"middle","description":"Задачи писать тексты","salary":""}
  self.assertEqual(q.market_guess(e),"140–225 тыс. ₽/мес")
  self.assertEqual(q.market_guess(dict(e,salary="120 000 ₽")),"")
  self.assertEqual(q.market_guess(dict(e,description="Частичная занятость, редактура интерфейсов")),"")
 def test_unknown_employer_remains_unknown(self):
  self.assertEqual(q.employer("Копирайтер\nМосква\nНужен опыт"),q.UNKNOWN)
if __name__=="__main__":unittest.main()
