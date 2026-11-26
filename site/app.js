"use strict";
let all=[],filtered=[],shown=15,lastTrigger=null;
const $=id=>document.getElementById(id);
const make=(tag,cls,value)=>{
 const el=document.createElement(tag);
 if(cls)el.className=cls;
 if(value!==undefined&&value!==null)el.textContent=String(value);
 return el;
};
const safeDate=s=>{
 if(!s)return "нет данных";
 const d=new Date(s);
 if(Number.isNaN(d.getTime()))return "нет данных";
 return d.toLocaleString("ru-RU",{timeZone:"Europe/Moscow",day:"numeric",month:"long",hour:"2-digit",minute:"2-digit"})+" МСК";
};
const format=j=>j.work_format||(/гибрид/i.test(j.location||"")?"Гибрид":/удал/i.test(j.location||"")?"Удалённо":/офис/i.test(j.location||"")?"Офис":"");
const level=j=>j.level||(/стаж|intern/i.test(j.title)?"intern":/junior|младш/i.test(j.title)?"junior":/senior|старш/i.test(j.title)?"senior":/lead|глав|руковод/i.test(j.title)?"lead":"");
const city=j=>j.city||((j.location||"").replace(/\s*[,;].*/,"")||"");
const salaryNumber=s=>{const m=(s||"").replace(/\s/g,"").match(/\d{5,7}/);return m?Number(m[0]):0};
const seen=j=>j.first_seen_at||j.seen_at||"";
const hint="Это не оценка работодателя и не рейтинг вакансий. Метка означает только объём информации в исходном объявлении; отсутствие зарплаты само по себе не делает работодателя хуже.";
function salaryDisplay(j,parent,modal=false){
 if(j.salary){parent.append(make(modal?"div":"p",modal?"modal-pay":"salary-label",j.salary));return}
 if(j.salary_estimate&&j.salary_estimate_basis>=3){
  const p=make("p","salary-estimate","Ориентир по нашим данным: "+j.salary_estimate);
  p.append(make("span","","Оценка по "+j.salary_estimate_basis+" другим вакансиям, не предложение работодателя"));
  parent.append(p);
 }
}
function qualityTag(job){
 const wrap=make("div","score");
 const quality=window.JobText.descriptionLabel(job.description);
 wrap.append(make("span","score-caption","Описание: "+quality));
 const info=make("span","info","i");
 info.tabIndex=0;info.dataset.hint=hint;
 info.setAttribute("role","note");
 info.setAttribute("aria-label",hint);
 info.setAttribute("title",hint);
 info.addEventListener("click",e=>{e.preventDefault();e.stopPropagation();info.focus()});
 info.addEventListener("keydown",e=>{
  if(e.key==="Enter"||e.key===" "){e.preventDefault();e.stopPropagation();info.focus()}
 });
 wrap.append(info);
 return wrap;
}
function card(job){
 const button=make("button","job");
 button.type="button";button.addEventListener("click",()=>openJob(job,button));
 const body=make("div");
 body.append(make("h3","",job.title),make("div","company",job.company||"Работодатель не указан"));
 salaryDisplay(job,body);
 const tags=make("div","tags");
 const values=[job.category,format(job),city(job),job.level||""];
 [...new Set(values.filter(Boolean))].forEach(text=>tags.append(make("span","tag",text)));
 body.append(tags);
 button.append(body,qualityTag(job));
 return button;
}
function sectionToElement(section){
 const wrapper=make("section","modal-section");
 wrapper.append(make("h3","",section.title));
 const items=section.items.filter(Boolean);
 if(section.kind==="overview"){
  for(const item of items)wrapper.append(make("p","",item));
 }else{
  const list=make("ul");
  for(const item of items)list.append(make("li","",item));
  wrapper.append(list);
 }
 return wrapper;
}
function openJob(job,button){
 lastTrigger=button;
 const content=$("detailsContent");
 content.replaceChildren(make("h2","",job.title));
 const company=job.company||"Работодатель не указан";
 content.append(make("p","muted",company));
 const meta=make("div","modal-meta");
 [...new Set([job.category,format(job),job.location||city(job),job.level].filter(Boolean))]
  .forEach(x=>meta.append(make("span","tag",x)));
 content.append(meta);
 salaryDisplay(job,content,true);
 const intro=make("p","modal-clarification","Описание структурировано автоматически на основе текста первоисточника. Содержание условий не изменяем.");
 content.append(intro);
 const sections=window.JobText.parseSections(job.description||"",job.title);
 let conditions=null;
 for(const part of sections){
  if(part.kind==="conditions"){conditions=part;continue}
  content.append(sectionToElement(part));
 }
 // Conditions are grouped last. Always display what is explicitly known.
 const conditionItems=[];
 if(job.location)conditionItems.push("Место работы: "+job.location);
 if(format(job))conditionItems.push("Формат: "+format(job));
 if(job.salary)conditionItems.push("Зарплата, указанная работодателем: "+job.salary);
 if(conditions)conditionItems.push(...conditions.items);
 if(conditionItems.length)content.append(sectionToElement({kind:"conditions",title:"Условия",items:[...new Set(conditionItems)]}));
 const note=make("p","modal-clarification","Описание: "+window.JobText.descriptionLabel(job.description)+". "+hint);
 content.append(note);
 const link=make("a","apply","Перейти к отклику ↗");
 link.href=job.url;link.target="_blank";link.rel="noopener noreferrer";
 content.append(link);
 if((job.sources||[]).length>1){
  const sources=make("div","modal-links");
  sources.append(make("h3","","Другие источники"));
  for(const source of job.sources){
   const a=make("a","source-link",source.name||"Первоисточник");
   a.href=source.url;a.target="_blank";a.rel="noopener noreferrer";sources.append(a);
  }
  content.append(sources);
 }
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
  return true;
 });
 filtered.sort($("sort").value==="score"?
  (a,b)=>(b.description||"").length-(a.description||"").length:
  (a,b)=>seen(b).localeCompare(seen(a)));
 shown=15;draw();
}
function draw(){
 const root=$("jobs");root.replaceChildren();
 $("count").textContent=filtered.length+" вакансий по выбранным фильтрам";
 if(!filtered.length){
  const box=make("div","empty");
  box.append(make("b","","Пока ничего не найдено"),
   make("span","","В ленте только вакансии из проверенных источников. Сбрось фильтры или возвращайся после обновления."));
  root.append(box);
 }else filtered.slice(0,shown).forEach(j=>root.append(card(j)));
 $("more").hidden=shown>=filtered.length;
}
async function init(){
 try{
  const response=await fetch("./jobs.json",{cache:"no-store"});
  if(!response.ok)throw Error("HTTP "+response.status);
  const data=await response.json();
  all=Array.isArray(data.jobs)?data.jobs:[];
  $("lastUpdated").textContent="Последнее обновление вакансий: "+safeDate(data.updated_at);
  $("updated").textContent="Проверено: "+safeDate(data.updated_at);
  $("total").textContent=String(all.length);
  $("sources").textContent=String(window.JobText.checkedSources(data.status));
  const cities=[...new Set(all.map(city).filter(x=>x&&x!=="Удалённо"))].sort((a,b)=>a.localeCompare(b,"ru"));
  cities.forEach(x=>{const opt=make("option","",x);opt.value=x;$("city").append(opt)});
  filter();
 }catch(e){
  $("lastUpdated").textContent="Последнее обновление: данные недоступны";
  $("count").textContent="Не удалось загрузить вакансии";
  $("jobs").append(make("div","empty","Ошибка загрузки данных. Попробуй обновить страницу."));
 }
}
["query","category","workFormat","level","city","salary","sort"].forEach(x=>
 $(x).addEventListener(x==="query"?"input":"change",filter));
$("more").addEventListener("click",()=>{shown+=15;draw()});
$("clear").addEventListener("click",()=>{
 for(const key of ["query","category","workFormat","level","city","salary"])$(key).value="";
 $("sort").value="fresh";filter();
});
$("close").addEventListener("click",()=>$("details").close());
$("details").addEventListener("click",e=>{
 const dialog=$("details");
 if(e.target!==dialog)return;
 const rect=dialog.getBoundingClientRect();
 if(e.clientX<rect.left||e.clientX>rect.right||e.clientY<rect.top||e.clientY>rect.bottom){
  dialog.close();
 }
});
$("details").addEventListener("close",()=>{
 if(lastTrigger&&lastTrigger.isConnected)lastTrigger.focus({preventScroll:true});
 lastTrigger=null;
});
init();
