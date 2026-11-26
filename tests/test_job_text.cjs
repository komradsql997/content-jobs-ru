const assert=require("node:assert/strict");
const test=require("node:test");
const fs=require("node:fs");
const path=require("node:path");
const helper=require("../site/job-text.js");

test("extracts semantic sections from collapsed career vacancy text",()=>{
 const t="Компания ищет UX-редактора. Что делать: Писать тексты для интерфейсов Совместно обсуждать сценарии Что уметь: Работать в Figma Иметь портфолио Что предлагают: Удалённую работу Оформление по ТК РФ";
 const sections=helper.parseSections(t);
 assert.deepEqual(sections.map(s=>s.kind),["overview","tasks","requirements","conditions"]);
 assert.ok(sections.find(s=>s.kind==="tasks").items.length>=2);
 assert.ok(sections.find(s=>s.kind==="conditions").items.join(" ").includes("ТК РФ"));
});
test("parses headings preserved in multiline Telegram post",()=>{
 const s=helper.parseSections("Редактор в компании\nЗадачи:\n• Писать новости\n• Редактировать статьи\nТребования:\n• Опыт 2 года");
 assert.deepEqual(s.map(p=>p.kind),["overview","tasks","requirements"]);
});
test("does not fabricate tasks when headers are missing",()=>{
 const s=helper.parseSections("Ищем автора текстов для блога. Портфолио необходимо.");
 assert.equal(s.length,1);assert.equal(s[0].kind,"overview");
});
test("qualitative description badge is independent of numeric score",()=>{
 assert.equal(helper.descriptionLabel("x".repeat(600)),"подробное");
 assert.equal(helper.descriptionLabel("x".repeat(250)),"основное");
 assert.equal(helper.descriptionLabel("Небольшое объявление"),"краткое");
});
test("counts successfully read sources, not channels with vacancies only",()=>{
 const status={"А":{status:"FOUND",listing_pages:1,saved:1},
 "Б":{status:"NO_MATCHES_IN_CHECKED_PAGES",listing_pages:1,saved:0},
 "В":{status:"FETCH_ERROR",listing_pages:0,saved:0},
 "Telegram @x":{status:"FOUND",saved:2},
 "Telegram @y":{status:"NO_MATCHES_IN_RECENT_PUBLIC_POSTS",saved:0},
 "Telegram @z":{status:"ROBOTS_UNAVAILABLE_OR_DISALLOWED",saved:0}};
 assert.equal(helper.checkedSources(status),4);
});
test("modal supports backdrop and escape and uses semantic parser",()=>{
 const html=fs.readFileSync(path.join(__dirname,"../site/index.html"),"utf8");
 const app=fs.readFileSync(path.join(__dirname,"../site/app.js"),"utf8");
 assert.match(html,/class="footer-link" href="https:\/\/t\.me\/leadofcringejobs"/);
 assert.doesNotMatch(html,/Пока только российские компании/);
 assert.match(app,/getBoundingClientRect/);
 assert.match(app,/parseSections/);
 assert.doesNotMatch(app,/job\.score\+"\/100"/);
});
