(function(root,factory){
  const api=factory();
  if(typeof module==="object"&&module.exports)module.exports=api;
  if(root)root.JobText=api;
})(typeof globalThis==="object"?globalThis:null,function(){
  "use strict";
  const labels={overview:"О вакансии",tasks:"Что делать",requirements:"Что ожидают от кандидата",conditions:"Условия"};
  const definitions=[
    {kind:"tasks",text:/^(?:какие задачи вас ждут|чем предстоит заниматься|что предстоит делать|что нужно делать|что делать|ваши задачи|основные задачи|обязанности|задачи)(?![а-яё])/i},
    {kind:"requirements",text:/^(?:что уметь|что мы жд[её]м|что ожидаем|мы ожидаем|кого мы ищем|наши ожидания|требования к соискателю|требования к кандидату|требования|что потребуется|будет плюсом|желательно)(?![а-яё])/i},
    {kind:"conditions",text:/^(?:что предлагают|что предлагаем|мы предлагаем|условия работы|формат работы|уровень заработной платы|условия|что вы получите|бонусы|что дадим|предлагаем)(?![а-яё])/i},
    {kind:"overview",text:/^(?:описание вакансии|немного о работодателе|о вакансии|о компании)(?![а-яё])/i}
  ];
  const headerRegex=/(?:^|\s)(какие задачи вас ждут|чем предстоит заниматься|что предстоит делать|что нужно делать|что делать|ваши задачи|основные задачи|обязанности|задачи|что уметь|что мы жд[её]м|что ожидаем|мы ожидаем|кого мы ищем|наши ожидания|требования к соискателю|требования к кандидату|требования|что потребуется|будет плюсом|желательно|что предлагают|что предлагаем|мы предлагаем|условия работы|формат работы|уровень заработной платы|условия|что вы получите|бонусы|что дадим|предлагаем|описание вакансии|немного о работодателе|о вакансии|о компании)(?=\s|:|：|—|–|$)/gi;
  const actionVerbs=/\s+(?=(?:Писать|Разрабатывать|Редактировать|Проверять|Организовывать|Создавать|Вести|Совместно|Следить|Предлагать|Иметь|Понимать|Работать|Применять|Самостоятельно|Уметь|Готовить|Анализировать|Публиковать|Поддерживать|ДМС|Оформление|Пятидневную|Удал[её]нную|Бесплатное|Возможность|Скидки|Корпоративные|Продуманную|Профессиональное|Получать|Отслеживать|Проведение|4 дополнительных)(?=[\s,.;:!?]|$))/g;
  const dangling=/(\b(?:и|или|но|от|до|без|с|со|по|на|для|под|в|к|у|за|из|после)\s*|[,;:—–-])$/i;
  function normalize(value){
    return String(value||"").replace(/\r\n?/g,"\n").replace(/\u00a0/g," ")
      .replace(/[ \t]+/g," ").replace(/ *\n */g,"\n").replace(/\n{3,}/g,"\n\n").trim();
  }
  function kindForHeading(heading){
    for(const d of definitions)if(d.text.test(heading.toLowerCase().trim()))return d.kind;
    return "overview";
  }
  function splitLong(text,kind="overview"){
    const raw=normalize(text);
    if(!raw)return [];
    const merged=[];
    for(const original of raw.split(/\n+/)){
      const line=original.trim();
      if(!line||/^[\s➖▬—–\-/⚡📣•·]+$/u.test(line))continue;
      const bullet=/^(?:[•●]\s+|[-–—]\s+)/.test(line);
      const cleaned=line.replace(/^(?:[•●]\s+|[-–—]\s+)/,"").trim();
      const prev=merged[merged.length-1];
      // HTML inline fragments must not become separate bullets.
      if(prev&&!bullet&&!/[.!?;]$/.test(prev)&&(/^[а-яё]/.test(cleaned)||dangling.test(prev)))
        merged[merged.length-1]=prev+" "+cleaned;
      else merged.push(cleaned);
    }
    const items=[];
    for(const line of merged){
      const parts=kind!=="overview"&&line.length>40?
        line.replace(actionVerbs,"\n").split("\n"): [line];
      // Never split at arbitrary word counts or ordinary nouns like "задачи".
      for(const part of parts)if(part.trim())items.push(part.trim());
    }
    return items;
  }
  function parseSections(description,title){
    let raw=normalize(description);
    raw=raw.replace(/(?:^|\n)\s*(?:➖\s*\n){2,}[\s\S]*$/u,"");
    raw=raw.replace(/(?:^|\n)\s*(?:📣\s*\n)?Разместить ваканси[юи][\s\S]*$/iu,"");
    raw=raw.replace(/(?:^|\n)\s*Получать больше вакансий[\s\S]*$/iu,"");
    const currentTitle=normalize(title);
    if(currentTitle&&raw.toLowerCase().startsWith(currentTitle.toLowerCase())){
      raw=raw.slice(currentTitle.length).trim();
    }
    if(!raw)return [];
    const markers=[];
    for(const match of raw.matchAll(headerRegex)){
      const h=match[1];
      const start=match.index+match[0].length-h.length;
      const bodyStart=match.index+match[0].length;
      const before=raw.slice(0,start),after=raw.slice(bodyStart);
      const beginsLine=start===0||/\n\s*$/.test(before);
      const separator=/^\s*[:：—–]/.test(after);
      const generic=/^(?:задачи|обязанности|требования|условия|бонусы|предлагаем|желательно|описание вакансии)$/i.test(h);
      if(generic&&!separator&&!beginsLine)continue;
      if(!generic&&!separator&&!beginsLine&&h[0]===h[0].toLocaleLowerCase("ru"))continue;
      markers.push({start,bodyStart,kind:kindForHeading(h)});
    }
    if(!markers.length)return [{kind:"overview",title:labels.overview,items:splitLong(raw)}];
    const sections=[];
    const intro=raw.slice(0,markers[0].start).trim();
    if(intro)sections.push({kind:"overview",title:labels.overview,items:splitLong(intro)});
    for(let i=0;i<markers.length;i++){
      const start=markers[i].bodyStart,end=i+1<markers.length?markers[i+1].start:raw.length;
      const block=raw.slice(start,end).replace(/^[\s:：—–-]+/,"").trim();
      const kind=markers[i].kind;
      const items=splitLong(block,kind);
      if(!items.length)continue;
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
