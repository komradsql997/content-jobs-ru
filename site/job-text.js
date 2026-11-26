(function(root,factory){
  const api=factory();
  if(typeof module==="object"&&module.exports)module.exports=api;
  if(root)root.JobText=api;
})(typeof globalThis==="object"?globalThis:null,function(){
  "use strict";
  const labels={overview:"О вакансии",tasks:"Что делать",requirements:"Что ожидают от кандидата",conditions:"Условия"};
  const definitions=[
    {kind:"tasks",text:/^(?:какие задачи вас ждут|чем предстоит заниматься|что предстоит делать|что делать|ваши задачи|основные задачи|обязанности|задачи)(?![а-яё])/i},
    {kind:"requirements",text:/^(?:что уметь|что мы жд[её]м|что ожидаем|кого мы ищем|наши ожидания|требования к кандидату|требования|что потребуется|будет плюсом|желательно)(?![а-яё])/i},
    {kind:"conditions",text:/^(?:что предлагают|что предлагаем|мы предлагаем|условия работы|условия|что вы получите|бонусы|что дадим|предлагаем)(?![а-яё])/i},
    {kind:"overview",text:/^(?:описание вакансии|о вакансии|о компании)(?![а-яё])/i}
  ];
  const headerRegex=/(?:^|\s)(какие задачи вас ждут|чем предстоит заниматься|что предстоит делать|что делать|ваши задачи|основные задачи|обязанности|задачи|что уметь|что мы жд[её]м|что ожидаем|кого мы ищем|наши ожидания|требования к кандидату|требования|что потребуется|будет плюсом|желательно|что предлагают|что предлагаем|мы предлагаем|условия работы|условия|что вы получите|бонусы|что дадим|предлагаем|описание вакансии|о вакансии|о компании)(?=\s|:|：|—|–|$)/gi;
  const actionVerbs=/\s+(?=(?:Писать|Разрабатывать|Редактировать|Проверять|Организовывать|Создавать|Вести|Совместно|Следить|Предлагать|Иметь|Понимать|Работать|Применять|Самостоятельно|Уметь|Готовить|Анализировать|Публиковать|Поддерживать|ДМС|Оформление|Пятидневную|Удал[её]нную|Бесплатное|Возможность)\b)/g;
  function normalize(value){
    return String(value||"").replace(/\r\n?/g,"\n").replace(/\u00a0/g," ")
      .replace(/[ \t]+/g," ").replace(/ *\n */g,"\n").replace(/\n{3,}/g,"\n\n").trim();
  }
  function kindForHeading(heading){
    for(const d of definitions)if(d.text.test(heading.toLowerCase().trim()))return d.kind;
    return "overview";
  }
  function splitLong(text){
    const raw=normalize(text).replace(/^[•●\-–—]\s*/gm,"").trim();
    if(!raw)return [];
    let parts=raw.split(/\n+/).map(x=>x.trim()).filter(Boolean);
    if(parts.length<2&&raw.length>140){
      parts=raw.replace(actionVerbs,"\n").split(/\n+/).map(x=>x.trim()).filter(Boolean);
    }
    if(parts.length<2&&raw.length>280){
      parts=raw.split(/(?<=[.!?;])\s+(?=[А-ЯЁA-Z])/).map(x=>x.trim()).filter(Boolean);
    }
    if(parts.length<2&&raw.length>340){
      const words=raw.split(" "),chunks=[];let current="";
      for(const word of words){
        if(current.length>240&&current.length+word.length>300){chunks.push(current.trim());current="";}
        current+=(current?" ":"")+word;
      }
      if(current)chunks.push(current.trim());
      parts=chunks;
    }
    return parts.map(x=>x.replace(/^[•●\-–—]\s*/,"").trim()).filter(Boolean);
  }
  function parseSections(description,title){
    let raw=normalize(description);
    const currentTitle=normalize(title);
    if(currentTitle&&raw.toLowerCase().startsWith(currentTitle.toLowerCase())){
      raw=raw.slice(currentTitle.length).trim();
    }
    if(!raw)return [];
    const markers=[];
    for(const match of raw.matchAll(headerRegex)){
      const h=match[1];
      const start=match.index+(match[0].startsWith(" ")?1:0);
      const bodyStart=match.index+match[0].length;
      markers.push({start,bodyStart,kind:kindForHeading(h)});
    }
    if(!markers.length)return [{kind:"overview",title:labels.overview,items:splitLong(raw)}];
    const sections=[];
    const intro=raw.slice(0,markers[0].start).trim();
    if(intro)sections.push({kind:"overview",title:labels.overview,items:splitLong(intro)});
    for(let i=0;i<markers.length;i++){
      const start=markers[i].bodyStart,end=i+1<markers.length?markers[i+1].start:raw.length;
      const block=raw.slice(start,end).replace(/^[\s:：—–-]+/,"").trim();
      const items=splitLong(block);
      if(!items.length)continue;
      const kind=markers[i].kind;
      const previous=sections[sections.length-1];
      if(previous&&previous.kind===kind){previous.items.push(...items)}
      else sections.push({kind,title:labels[kind],items});
    }
    return sections.length?sections:[{kind:"overview",title:labels.overview,items:splitLong(raw)}];
  }
  function descriptionLabel(description){
    const text=normalize(description);
    if(text.length>=550)return "подробное";
    if(text.length>=180)return "основное";
    return "краткое";
  }
  function checkedSources(status){
    return Object.entries(status||{}).filter(([key,value])=>{
      if(!value||typeof value!=="object")return false;
      if(key.startsWith("Telegram @")){
        return value.status==="FOUND"||value.status==="NO_MATCHES_IN_RECENT_PUBLIC_POSTS";
      }
      return Number(value.listing_pages||0)>0||Number(value.saved||0)>0;
    }).length;
  }
  return {normalize,parseSections,descriptionLabel,checkedSources};
});
