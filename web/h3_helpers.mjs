export const cloneJSON=value=>JSON.parse(JSON.stringify(value||{}));

export function fitResolutionToAspect(sourceWidth,sourceHeight,targetWidth,targetHeight){
  const ratio=Number(sourceWidth)/Number(sourceHeight);
  const targetPixels=Number(targetWidth)*Number(targetHeight);
  if(!(ratio>0)||!(targetPixels>0)) return {width:targetWidth,height:targetHeight};
  let best=null;
  for(let width=32;width<=1344;width+=32){
    for(let height=32;height<=1344;height+=32){
      if(Math.min(width,height)>768||width*height>targetPixels) continue;
      const aspectError=Math.abs(Math.log((width/height)/ratio));
      const areaError=Math.abs(Math.log((width*height)/targetPixels));
      const score=aspectError*12+areaError;
      if(!best||score<best.score) best={width,height,score};
    }
  }
  return best?{width:best.width,height:best.height}:{width:targetWidth,height:targetHeight};
}

export const mediaKey=item=>`${item?.type||"output"}|${String(item?.subfolder||"").replace(/\\/g,"/")}|${item?.filename||item?.video||""}`;

export function resolveNodeState(properties,defaults={}){
  const own=properties?.h3one;
  return own?.schema===1&&own.state?cloneJSON(own.state):cloneJSON(defaults);
}

export function selectDefaults(state,fields){
  const out={};
  for(const key of fields||[])if(state?.[key]!==undefined)out[key]=cloneJSON(state[key]);
  return out;
}

export function selectSolProvider(capabilities){
  const sol=capabilities?.features?.sol;
  if(!sol?.available) return "";
  return sol.provider==="saganaki"?"saganaki":sol.provider==="kijai"?"kijai":"";
}
