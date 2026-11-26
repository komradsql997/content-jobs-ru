const assert=require("node:assert/strict");
const test=require("node:test");
const fs=require("node:fs");
const path=require("node:path");
const helper=require("../site/job-text.js");
test("does not split 'задачи до результата' into separate item",()=>{
 const s="Что уметь: Иметь опыт работы Самостоятельно организовывать работу и доводить задачи до результата Уметь выстраивать коммуникацию";
 const p=helper.parseSections(s);
 assert.equal(p.length,1);
 assert.equal(p[0].kind,"requirements");
 assert.ok(p[0].items.some(x=>x==="Самостоятельно организовывать работу и доводить задачи до результата"),JSON.stringify(p));
 assert.ok(!p[0].items.includes("до результата"));
});
test("keeps 'от партнёров' with discounts",()=>{
 const s="Что предлагают: ДМС со стоматологией после испытательного срока 4 дополнительных выходных в год после испытательного срока Скидки и бонусы от партнёров, включая Skillbox Корпоративные мероприятия";
 const p=helper.parseSections(s);
 assert.deepEqual(p.map(x=>x.kind),["conditions"]);
 assert.ok(p[0].items.some(x=>x.startsWith("Скидки и бонусы от партнёров")),JSON.stringify(p));
});
test("joins wrapped fragments but respects bullets",()=>{
 const p=helper.parseSections("Условия:\n• Скидки и бонусы\nот партнёров, включая Skillbox\n• ДМС со стоматологией");
 assert.deepEqual(p[0].items,["Скидки и бонусы от партнёров, включая Skillbox","ДМС со стоматологией"]);
});
test("collapsed corporate headings parse",()=>{
 const p=helper.parseSections("Точка ищет UX-редактора. Что делать: Писать тексты интерфейсов Совместно обсуждать сценарии Что уметь: Работать в Figma Иметь портфолио Что предлагают: Удалённую работу Оформление по ТК РФ");
 assert.deepEqual(p.map(x=>x.kind),["overview","tasks","requirements","conditions"]);
 assert.ok(p[1].items.length>=2);
});
test("Telegram multiline headings parse",()=>{
 const p=helper.parseSections("Редактор\nЗадачи:\n• Писать новости\n• Редактировать статьи\nТребования:\n• Опыт от 2 лет");
 assert.deepEqual(p.map(x=>x.kind),["overview","tasks","requirements"]);
});
test("do not hallucinate structure",()=>{
 const p=helper.parseSections("Нужен редактор со знанием русского языка.");
 assert.equal(p.length,1);assert.equal(p[0].kind,"overview");
});
test("counter counts readable sources",()=>{
 const status={A:{status:"FOUND",listing_pages:1},B:{status:"FETCH_ERROR"},C:{listing_pages:1},
 "Telegram @a":{status:"FOUND"},"Telegram @b":{status:"NO_MATCHES_IN_RECENT_PUBLIC_POSTS"}};
 assert.equal(helper.checkedSources(status),4);
});
test("list omits ambiguous detail labels and estimates",()=>{
 const app=fs.readFileSync(path.join(__dirname,"../site/app.js"),"utf8");
 const html=fs.readFileSync(path.join(__dirname,"../site/index.html"),"utf8");
 const detail=fs.readFileSync(path.join(__dirname,"../site/job-detail.js"),"utf8");
 assert.doesNotMatch(app,/make\("span","job-open","Подробнее"\)/);
 assert.doesNotMatch(app,/Ориентир по нашим данным/);
 assert.doesNotMatch(html,/01 \/ Вакансии/);
 assert.match(detail,/Предположение по рынку РФ/);
 assert.doesNotMatch(detail,/Оценка по.*ваканси/);
});
test("a post promo footer is removed without affecting actual requirements",()=>{
 const raw="Копирайтер-редактор. Что нужно делать:\n• Писать статьи\n• Редактировать новости\n➖\n➖\n📣\nРазместить вакансию\n/\nрекламу\n⚡️\nПолучать больше вакансий";
 const p=helper.parseSections(raw);
 assert.ok(p.some(x=>x.kind==="tasks"));
 assert.ok(!JSON.stringify(p).includes("Получать больше"));
 assert.ok(!JSON.stringify(p).includes("Разместить вакансию"));
});
test("list uses shareable pages and hides scoring",()=>{
 const index=fs.readFileSync(path.join(__dirname,"../site/index.html"),"utf8");
 const app=fs.readFileSync(path.join(__dirname,"../site/app.js"),"utf8");
 assert.match(index,/class="hero-strip"/);
 assert.doesNotMatch(index,/<dialog/);
 assert.doesNotMatch(index,/value="score"/);
 assert.match(app,/\.\/v\/.*encodeURIComponent\(j\.id\)/);
 assert.doesNotMatch(app,/qualityTag|score-caption|\.score\b/);
});
