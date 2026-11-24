let all=[],filtered=[],shown=15;
const $=id=>document.getElementById(id), text=(el,val)=>{el.textContent=val||"";return el};
const make=(tag,cls,value)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(value!==undefined)e.textContent=value;return e};
const date=s=>s?new Date(s).toLocaleString("ru-RU",{timeZone:"Europe/Moscow",day:"numeric",month:"long",hour:"2-digit",minute:"2-digit"}):"данных пока нет";
function card(job){
 const b=make("button","job");b.type="button";b.onclick=()=>open(job);
 const body=make("div");const h=make("h3","",job.title);body.append(h,make("div","company",job.company));
 body.append(make("p","salary-label",job.salary||"Зарплата не указана"));
 const tags=make("div","tags");[job.category,job.location].filter(Boolean).forEach(s=>tags.append(make("span","tag",s)));body.append(tags);
 const score=make("div","score");score.append(make("strong","",String(job.score??"—")),make("small","","из 100"));
 b.append(body,score);return b;
}
function open(job){
 const c=$("detailsContent");c.replaceChildren(make("h2","",job.title),make("p","muted",job.company+" · "+(job.location||"Место уточняется")),make("h3","",job.salary||"Зарплата не указана"));
 c.append(make("p","", "Информативность объявления: "+job.score+"/100"));
 c.append(make("p","desc",job.description||"Подробности — у работодателя."));
 const a=make("a","apply","Перейти к отклику ↗");a.href=job.url;a.target="_blank";a.rel="noopener noreferrer";c.append(a);
 if((job.sources||[]).length>1){c.append(make("h4","","Другие источники"));job.sources.forEach(s=>{const l=make("a","source-link",s.name);l.href=s.url;l.target="_blank";l.rel="noopener noreferrer";c.append(l)})}
 $("details").showModal();
}
function filter(){
 const q=$("query").value.trim().toLocaleLowerCase("ru"),cat=$("category").value,hasSalary=$("salary").value==="yes";
 filtered=all.filter(j=>(!q||[j.title,j.company,j.description].join(" ").toLocaleLowerCase("ru").includes(q))&&(!cat||j.category===cat)&&(!hasSalary||!!j.salary));
 filtered.sort($("sort").value==="score"?(a,b)=>b.score-a.score:(a,b)=>(b.seen_at||"").localeCompare(a.seen_at||""));
 shown=15;draw();
}
function draw(){
 const root=$("jobs");root.replaceChildren();
 $("count").textContent=filtered.length+" вакансий по выбранным фильтрам";
 if(!filtered.length){const box=make("div","empty");box.append(make("b","","Пока ничего не найдено"),make("span","","Мы показываем только вакансии, полученные из источников. Попробуй сбросить фильтры или вернись после следующего обновления."));root.append(box)}
 filtered.slice(0,shown).forEach(j=>root.append(card(j)));
 $("more").hidden=shown>=filtered.length;
}
async function init(){
 try{
 const res=await fetch("./jobs.json",{cache:"no-cache"});if(!res.ok)throw Error("HTTP "+res.status);
 const data=await res.json();all=Array.isArray(data.jobs)?data.jobs:[];
 $("updated").textContent="Проверено: "+date(data.updated_at);
 $("total").textContent=String(all.length);
 $("sources").textContent=String(new Set(all.flatMap(j=>(j.sources||[]).map(s=>s.name))).size);
 const cats=[...new Set(all.map(j=>j.category).filter(Boolean))].sort();
 cats.forEach(c=>{const o=make("option","",c);o.value=c;$("category").append(o)});
 filter();
 }catch(e){$("count").textContent="Не удалось загрузить вакансии";$("jobs").append(make("div","empty","Проблема с загрузкой данных. Попробуй обновить страницу."))}
}
["query","category","salary","sort"].forEach(k=>$(k).addEventListener(k==="query"?"input":"change",filter));
$("more").onclick=()=>{shown+=15;draw()};
$("clear").onclick=()=>{$("query").value="";$("category").value="";$("salary").value="";$("sort").value="fresh";filter()};
$("close").onclick=()=>$("details").close();
init();
