import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import build_job_pages as b
class JobPageTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.site=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def test_link_is_stable_and_disambiguates_duplicate_titles(self):
  a={"title":"UX-редактор","company":"Компания","url":"https://example.com/job/1"}
  c=dict(a,url="https://example.com/job/2")
  self.assertNotEqual(b.stable_id(a),b.stable_id(c))
  self.assertEqual(b.stable_id(a),b.stable_id(dict(a,title="UX-редактор senior")))
 def test_page_contains_shareable_metadata_and_safe_json(self):
  j={"title":"Редактор </script><script>alert(1)</script>","company":"Компания",
     "url":"https://example.com/job/1","description":"Требования: опыт\nЧто делать: тексты"}
  page=b.render_page(j,True)
  self.assertIn('property="og:title"',page)
  self.assertIn('rel="canonical"',page)
  self.assertIn('id="vacancy-data"',page)
  self.assertNotIn('</script><script>alert(1)</script>',page)
  self.assertIn('job-detail.js',page)
 def test_expired_links_have_archived_status_and_then_prune(self):
  j={"title":"Редактор","company":"Компания","url":"https://example.com/job/1"}
  (self.site/"jobs.json").write_text(json.dumps({"jobs":[j]}),encoding="utf-8")
  count,active=b.build(self.site)
  self.assertEqual((count,active),(1,1))
  page=self.site/"v"/(b.stable_id(j)+".html")
  self.assertTrue(page.exists())
  (self.site/"jobs.json").write_text('{"jobs":[]}',encoding="utf-8")
  count,active=b.build(self.site)
  self.assertEqual((count,active),(1,0))
  self.assertIn('"active":false',page.read_text(encoding="utf-8"))
