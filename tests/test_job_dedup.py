import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from collect import make_job,merge_jobs,same_vacancy_text

class SyndicationTests(unittest.TestCase):
 def test_same_vacancy_from_two_sources_is_merged(self):
  body=" ".join(f"Готовить и публиковать SEO-статьи и лонгриды Нетологии на тему {i}. Работать с экспертами и редакторами, готовить материалы для публикации проекта {i}." for i in range(32))
  a=make_job("Редактор в Медиа","Нетология","https://netology.ru/job/123",body,"Россия")
  b=make_job("Редактор","Нетология","https://t.me/channel_name/456",body,"Россия")
  self.assertTrue(same_vacancy_text(a,b))
  result=merge_jobs([a],[b])
  self.assertEqual(len(result),1)
  self.assertEqual(result[0]["title"],"Редактор в Медиа")
  self.assertEqual(len(result[0]["sources"]),2)
 def test_unrelated_roles_remain_distinct(self):
  a=make_job("Редактор","Нетология","https://netology.ru/job/1","Писать статьи про SEO и создавать лонгриды для образовательной платформы. "*8,"Россия")
  b=make_job("SMM-менеджер","Нетология","https://netology.ru/job/2","Управлять SMM-командой и анализировать рекламные кампании в соцсетях. "*8,"Россия")
  self.assertFalse(same_vacancy_text(a,b))
  self.assertEqual(len(merge_jobs([a],[b])),2)
if __name__=="__main__":unittest.main()
