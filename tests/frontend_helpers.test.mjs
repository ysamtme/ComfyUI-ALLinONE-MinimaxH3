import assert from "node:assert/strict";
import {fitResolutionToAspect,mediaKey,resolveNodeState,selectDefaults,selectSolProvider} from "../web/h3_helpers.mjs";

assert.deepEqual(fitResolutionToAspect(2000,1501,1344,768),{width:1024,height:768});
assert.deepEqual(fitResolutionToAspect(1501,2000,1344,768),{width:768,height:1024});
assert.deepEqual(fitResolutionToAspect(2000,2000,1344,768),{width:768,height:768});
const extreme=fitResolutionToAspect(4000,500,1344,768);
assert.equal(extreme.width%32,0);
assert.equal(extreme.height%32,0);
assert.ok(extreme.width<=1344&&extreme.height<=768&&extreme.width*extreme.height<=1344*768);
assert.deepEqual(fitResolutionToAspect(0,0,960,544),{width:960,height:544});

assert.equal(mediaKey({type:"temp",subfolder:"preview\\x",filename:"same.mp4"}),"temp|preview/x|same.mp4");
assert.notEqual(mediaKey({type:"temp",filename:"same.mp4"}),mediaKey({type:"output",filename:"same.mp4"}));

const defaults={quality:"balanced",models:{unet:"default"}};
assert.deepEqual(resolveNodeState({},defaults),defaults);
const own={h3one:{schema:1,state:{prompt:"node prompt",models:{unet:"own"}}}};
const restored=resolveNodeState(own,defaults);
assert.equal(restored.prompt,"node prompt");
restored.models.unet="changed";
assert.equal(own.h3one.state.models.unet,"own");
assert.deepEqual(selectDefaults({prompt:"private",quality:"high",firstFrame:"input.png"},["quality"]),{quality:"high"});

assert.equal(selectSolProvider({features:{sol:{available:true,provider:"saganaki"}}}),"saganaki");
assert.equal(selectSolProvider({features:{sol:{available:true,provider:"kijai"}}}),"kijai");
assert.equal(selectSolProvider({features:{sol:{available:false,provider:"saganaki"}}}),"");

console.log("frontend helper tests passed");
