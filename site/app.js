"use strict";
let all=[],filtered=[],shown=15;
const $=id=>document.getElementById(id);
const make=(tag,cls,value)=>{const el=document.createElement(tag);if(cls)el.className=cls;if(value!==undefined&&value!==null)el.textContent=String(value);return el};
const safeDate=s=>{if(!s)return "нет данных";const d=new Date(s);return Number.isNaN(d.getTime())?"нет данных":d.toLocaleString("ru-RU",{timeZone:"Europe/Moscow",day:"numeric",month:"long",hour:"2-digit",minute:"2-digit"})+" МСК"};
const fmt=j=>j.work_format||(/гибрид/i.test(j.location||"")?"Гибрид":/удал/i.test(j.location||"")?"Удалённо":/офис/i.test(j.location||"")?"Офис":"");
const city=j=>j.city||((j.location||"").replace(/\s*[,;].*/,"")||"");
const salaryNumber=s=>{const m=(s||"").replace(/\s/g,"").match(/\d{5,7}/);return m?Number(m[0]):0};
const seen=j=>j.first_seen_at||j.seen_at||"";
const linkFor=j=>"./v/"+encodeURIComponent(j.id)+".html";
function salaryDisplay(j,parent){
 if(j.salary){parent.append(make("p","salary-label",j.salary));return}
 if(j.salary_estimate&&j.salary_estimate_basis>=3){const p=make("p","salary-estimate","Ориентир по нашим данным: "+j.salary_estimate);p.append(make("span","","Оценка по "+j.salary_estimate_basis+" другим вакансиям, не предложение работодателя"));parent.append(p)}
}
function card(j){
 const a=make("a","job");a.href=linkFor(j);
 const body=make("div","job-body");
 body.append(make("h3","",j.title),make("div","company",j.company||"Работодатель не указан"));
 salaryDisplay(j,body);
 const tags=make("div","tags");
 [...new Set([j.category,fmt(j),city(j),j.level].filter(Boolean))].forEach(x=>tags.append(make("span","tag",x)));
 body.append(tags);a.append(body,make("span","job-open","Подробнее"));return a;
}
function filter(){
 const q=$("query").value.trim().toLocaleLowerCase("ru"),cat=$("category").value,format=$("workFormat").value,lvl=$("level").value,ct=$("city").value,pay=$("salary").value;
 filtered=all.filter(j=>{
  if(q&&![j.title,j.company,j.description,j.category].join(" ").toLocaleLowerCase("ru").includes(q))return false;
  if(cat&&j.category!==cat)return false;
  if(format&&fmt(j)!==format)return false;
  if(lvl&&j.level!==lvl)return false;
  if(ct&&city(j)!==ct)return false;
  if(pay==="yes"&&!j.salary)return false;
  if(pay==="estimate"&&(!j.salary_estimate||j.salary_estimate_basis<3))return false;
  if(/^\d+$/.test(pay)&&Math.max(salaryNumber(j.salary),salaryNumber(j.salary_estimate))<Number(pay))return false;
  return true;
 });
 filtered.sort($("sort").value==="salaryFirst"?
  (a,b)=>Number(Boolean(b.salary))-Number(Boolean(a.salary))||seen(b).localeCompare(seen(a)):
  (a,b)=>seen(b).localeCompare(seen(a)));
 shown=15;draw();
}
function draw(){
 const root=$("jobs");root.replaceChildren();
 $("count").textContent=filtered.length+" вакансий по выбранным фильтрам";
 if(!filtered.length){const box=make("div","empty");box.append(make("b","","Пока ничего не найдено"),make("span","","Сбрось фильтры или возвращайся после обновления."));root.append(box)}
 else filtered.slice(0,shown).forEach(j=>root.append(card(j)));
 $("more").hidden=shown>=filtered.length;
}
async function init(){
 try{
  const res=await fetch("./jobs.json",{cache:"no-store"});
  if(!res.ok)throw Error("HTTP "+res.status);
  const data=await res.json();all=Array.isArray(data.jobs)?data.jobs:[];
  $("lastUpdated").textContent=safeDate(data.updated_at);
  $("total").textContent=String(all.length);
  $("sources").textContent=String(window.JobText.checkedSources(data.status));
  [...new Set(all.map(city).filter(c=>c&&c!=="Удалённо"))].sort((a,b)=>a.localeCompare(b,"ru")).forEach(c=>{const opt=make("option","",c);opt.value=c;$("city").append(opt)});
  filter();
 }catch(e){$("lastUpdated").textContent="недоступно";$("count").textContent="Не удалось загрузить вакансии";$("jobs").append(make("div","empty","Проверь соединение и обнови страницу."))}
}
["query","category","workFormat","level","city","salary","sort"].forEach(k=>$(k).addEventListener(k==="query"?"input":"change",filter));
$("more").onclick=()=>{shown+=15;draw()};
$("clear").onclick=()=>{["query","category","workFormat","level","city","salary"].forEach(k=>$(k).value="");$("sort").value="fresh";filter()};
init();
