"use strict";
(function(){
 const $=id=>document.getElementById(id);
 const make=(tag,cls,value)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(value!==undefined&&value!==null)e.textContent=String(value);return e};
 const data=JSON.parse($("vacancy-data").textContent),job=data.job||{};
 const root=$("vacancy-content"),title=job.title||"Вакансия";
 const safeLink=(raw)=>{try{const u=new URL(raw);return ["http:","https:"].includes(u.protocol)?u.href:""}catch{return ""}};
 const format=job.work_format||(/удал/i.test(job.location||"")?"Удалённо":/гибрид/i.test(job.location||"")?"Гибрид":/офис/i.test(job.location||"")?"Офис":"");
 const sectionElement=section=>{
  const outer=make("section","modal-section");
  outer.append(make("h2","",section.title));
  if(section.kind==="overview"){
   for(const item of section.items.filter(Boolean))outer.append(make("p","",item));
  }else{
   const ul=make("ul");
   for(const item of section.items.filter(Boolean))ul.append(make("li","",item));
   outer.append(ul);
  }
  return outer;
 };
 const head=make("section","job-header");
 head.append(make("h1","",title),make("p","job-subtitle",job.company||"Работодатель не указан"));
 const tags=make("div","tags");
 [...new Set([job.category,format,job.location,job.level].filter(Boolean))]
  .forEach(v=>tags.append(make("span","tag",v)));
 head.append(tags);
 if(job.salary){
  head.append(make("div","salary-label","Зарплата в объявлении: "+job.salary));
 }else if(job.salary_estimate){
  const box=make("p","salary-estimate","Наш ориентир: "+job.salary_estimate);
  box.append(make("span","","Предположение по рынку РФ. Работодатель зарплату не указал."));
  head.append(box);
 }else{
  head.append(make("p","salary-estimate","Зарплата не указана. Для проектной или частичной занятости месячный ориентир не рассчитываем."));
 }
 if(!data.active)head.append(make("p","job-availability","Вакансия больше не показывается в актуальной ленте. Проверь, открыта ли она, у работодателя."));
 const actions=make("div","job-actions");
 const target=safeLink(job.url);
 if(target){
  const a=make("a","apply","Перейти к отклику ↗");
  a.href=target;a.target="_blank";a.rel="noopener noreferrer";actions.append(a);
 }
 const copy=make("button","job-copy","Скопировать ссылку");copy.type="button";
 copy.addEventListener("click",async()=>{
  try{
   if(!navigator.clipboard?.writeText)throw new Error("Clipboard unavailable");
   await navigator.clipboard.writeText(location.href);
   copy.textContent="Ссылка скопирована";
  }catch{
   const input=make("input");input.value=location.href;input.readOnly=true;
   actions.append(input);input.select();
   copy.textContent="Скопируй выделенную ссылку";
  }
 });
 actions.append(copy);head.append(actions);root.append(head);
 const body=make("div","job-description");
 const sections=window.JobText.parseSections(job.description||"",title);
 let conditions=[];
 for(const section of sections){
  if(section.kind==="conditions")conditions.push(...section.items);
  else body.append(sectionElement(section));
 }
 const explicit=[];
 if(job.location)explicit.push("Место работы: "+job.location);
 if(format)explicit.push("Формат: "+format);
 if(job.salary)explicit.push("Оплата, указанная в вакансии: "+job.salary);
 conditions=[...new Set([...explicit,...conditions].filter(Boolean))];
 if(conditions.length)body.append(sectionElement({kind:"conditions",title:"Условия",items:conditions}));
 if(!sections.length)body.append(make("p","","Описание доступно по ссылке на первоисточник."));
 root.append(body);
 if((job.sources||[]).length>1){
  const sources=make("section","job-description modal-links");
  sources.append(make("h2","","Другие источники"));
  for(const item of job.sources){
   const u=safeLink(item.url);if(!u)continue;
   const link=make("a","source-link",item.name||"Первоисточник");
   link.href=u;link.target="_blank";link.rel="noopener noreferrer";sources.append(link);
  }
  root.append(sources);
 }
})();
