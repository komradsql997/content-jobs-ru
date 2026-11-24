
let all=[],filtered=[],shown=15;
const $=id=>document.getElementById(id);
const make=(tag,cls,value)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(value!==undefined)e.textContent=value;return e};
const date=s=>s?new Date(s).toLocaleString("ru-RU",{timeZone:"Europe/Moscow",day:"numeric",month:"long",hour:"2-digit",minute:"2-digit"})+" МСК":"данных пока нет";
const hint="Это оценка полноты описания, а не работодателя: учитываем указанные задачи, требования, зарплату, формат и возможность откликнуться.";
const format=j=>j.work_format||(/гибрид/i.test(j.location||"")?"Гибрид":/удал/i.test(j.location||"")?"Удалённо":/офис/i.test(j.location||"")?"Офис":"");
const level=j=>j.level||(/стаж|intern/i.test(j.title)?"intern":/junior|младш/i.test(j.title)?"junior":/senior|старш/i.test(j.title)?"senior":/lead|глав|руковод/i.test(j.title)?"lead":"");
const city=j=>j.city||((j.location||"").replace(/\s*[,;].*/,"")||"");
const salaryNumber=s=>{const m=(s||"").replace(/\s/g,"").match(/\d{5,7}/);return m?Number(m[0]):0};
const seen=j=>j.first_seen_at||j.seen_at||"";
function salaryDisplay(j,parent){
 if(j.salary){parent.append(make("p","salary-label",j.salary));return}
 if(j.salary_estimate&&j.salary_estimate_basis>=3){
  const p=make("p","salary-estimate","Ориентир по нашим данным: "+j.salary_estimate);
  p.append(make("span","","Оценка, не предложение работодателя · выборка "+j.salary_estimate_basis+" вакансий"));
  parent.append(p)
 }
}
function card(job){
 const b=make("button","job");b.type="button";b.onclick=()=>open(job);
 const body=make("div");body.append(make("h3","",job.title),make("div","company",job.company));
 salaryDisplay(job,body);
 const tags=make("div","tags");
 [job.category,format(job),city(job),job.level?job.level:""].filter(Boolean).forEach(x=>tags.append(make("span","tag",x)));
 body.append(tags);
 const score=make("div","score");score.append(make("strong","",String(job.score??"—")),make("small","","из 100"));
 const info=make("span","info","i");info.tabIndex=0;info.setAttribute("aria-label",hint);info.setAttribute("title",hint);info.dataset.hint=hint;
 info.onclick=e=>{e.stopPropagation(); e.preventDefault();info.focus()};
 info.onkeydown=e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();e.stopPropagation();info.focus()}};
 score.append(info);b.append(body,score);return b;
}
function open(job){
 const c=$("detailsContent");
 c.replaceChildren(make("h2","",job.title),make("p","muted",job.company+" · "+(job.location||"Место уточняется")));
 salaryDisplay(job,c);
 const s=make("p","","Информативность описания: "+job.score+"/100. "+hint);c.append(s);
 c.append(make("p","desc",job.description||"Подробности — у работодателя."));
 const a=make("a","apply","Перейти к отклику ↗");a.href=job.url;a.target="_blank";a.rel="noopener noreferrer";c.append(a);
 if((job.sources||[]).length>1){c.append(make("h4","","Другие источники"));job.sources.forEach(x=>{const l=make("a","source-link",x.name);l.href=x.url;l.target="_blank";l.rel="noopener noreferrer";c.append(l)})}
 $("details").showModal();
}
function filter(){
 const q=$("query").value.trim().toLocaleLowerCase("ru"),cat=$("category").value,fmt=$("workFormat").value,lvl=$("level").value,ct=$("city").value,pay=$("salary").value;
 filtered=all.filter(j=>{
  if(q&&![j.title,j.company,j.description,j.category].join(" ").toLocaleLowerCase("ru").includes(q))return false;
  if(cat&&j.category!==cat)return false;
  if(fmt&&format(j)!==fmt)return false;
  if(lvl&&level(j)!==lvl)return false;
  if(ct&&city(j)!==ct)return false;
  if(pay==="yes"&&!j.salary)return false;
  if(pay==="estimate"&&(!j.salary_estimate||j.salary_estimate_basis<3))return false;
  if(/^\d+$/.test(pay)&&Math.max(salaryNumber(j.salary),salaryNumber(j.salary_estimate))<Number(pay))return false;
  return true
 });
 filtered.sort($("sort").value==="score"?(a,b)=>(b.score||0)-(a.score||0):(a,b)=>seen(b).localeCompare(seen(a)));
 shown=15;draw();
}
function draw(){
 const root=$("jobs");root.replaceChildren();
 $("count").textContent=filtered.length+" вакансий по выбранным фильтрам";
 if(!filtered.length){
 const box=make("div","empty");
 box.append(make("b","","Пока ничего не найдено"),make("span","","Здесь показываются только реальные вакансии из подключённых источников. Можно сбросить фильтры или проверить сайт после обновления."));
 root.append(box);
 }else filtered.slice(0,shown).forEach(j=>root.append(card(j)));
 $("more").hidden=shown>=filtered.length;
}
async function init(){
 try{
 const res=await fetch("./jobs.json",{cache:"no-store"});if(!res.ok)throw Error("HTTP "+res.status);
 const data=await res.json();all=Array.isArray(data.jobs)?data.jobs:[];
 $("lastUpdated").textContent="Последнее обновление вакансий: "+date(data.updated_at);
 $("updated").textContent="Проверено: "+date(data.updated_at);
 $("total").textContent=String(all.length);
 $("sources").textContent=String(new Set(all.flatMap(j=>(j.sources||[]).map(s=>s.name))).size);
 const cities=[...new Set(all.map(city).filter(c=>c&&c!=="Удалённо"))].sort((a,b)=>a.localeCompare(b,"ru"));
 cities.forEach(c=>{const o=make("option","",c);o.value=c;$("city").append(o)});
 filter();
 }catch(e){$("lastUpdated").textContent="Последнее обновление: данные недоступны";$("count").textContent="Не удалось загрузить вакансии";$("jobs").append(make("div","empty","Ошибка загрузки данных. Попробуй обновить страницу."))}
}
["query","category","workFormat","level","city","salary","sort"].forEach(k=>$(k).addEventListener(k==="query"?"input":"change",filter));
$("more").onclick=()=>{shown+=15;draw()};
$("clear").onclick=()=>{["query","category","workFormat","level","city","salary"].forEach(k=>$(k).value="");$("sort").value="fresh";filter()};
$("close").onclick=()=>$("details").close();
init();
