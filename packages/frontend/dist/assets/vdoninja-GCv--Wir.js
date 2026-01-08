function n(){return"r58-vdo.itagenten.no"}function c(){return"https"}const u="studio",d="preke-r58-2024";function i(){var e,t;const o=`
/* R58 VDO.ninja Theme - Colors Only */
:root {
  --r58-bg: #0f172a;
  --r58-bg2: #1e293b;
  --r58-bg3: #334155;
  --r58-text: #f8fafc;
  --r58-muted: #94a3b8;
  --r58-blue: #3b82f6;
  --r58-green: #22c55e;
  --r58-gold: #f59e0b;
  --r58-border: #475569;
}
body { background: var(--r58-bg); color: var(--r58-text); }
#mainmenu, .controlButtons, #guestFeatures { background: var(--r58-bg2); }
button, .button { background: var(--r58-bg3); color: var(--r58-text); border-color: var(--r58-border); }
button:hover { background: var(--r58-blue); }
input, select, textarea { background: var(--r58-bg3); color: var(--r58-text); border-color: var(--r58-border); }
a { color: var(--r58-blue); }
.vidcon { background: var(--r58-bg2); border-color: var(--r58-border); border-radius: 8px; }
video { border-radius: 6px; }
`;if(typeof window<"u"&&((t=(e=window.location)==null?void 0:e.origin)!=null&&t.startsWith("file://")))return"";try{return"b64:"+btoa(unescape(encodeURIComponent(o)))}catch{return""}}function m(o){const e=n(),t=c(),r=new URL(`${t}://${e}/`);return r.searchParams.set("scene",""),r.searchParams.set("room",u),r.searchParams.set("cover",""),r.searchParams.set("quality","2"),r.searchParams.set("cleanoutput",""),r.searchParams.set("hideheader",""),r.searchParams.set("nologo",""),r.searchParams.set("whipout",o),r.searchParams.set("autostart",""),r.searchParams.set("videodevice","0"),r.searchParams.set("audiodevice","0"),r.searchParams.set("css",i()),r.toString()}function l(o,e={}){const t=n(),r=c(),a=new URL(`${r}://${t}/`);a.searchParams.set("scene",o.toString()),a.searchParams.set("room",e.room||u),a.searchParams.set("password",d),a.searchParams.set("cover",""),a.searchParams.set("cleanoutput",""),a.searchParams.set("hideheader",""),a.searchParams.set("nologo",""),a.searchParams.set("quality",(e.quality??2).toString()),e.muted&&a.searchParams.set("muted","");const s=i();return s&&a.searchParams.set("css",s),a.toString()}function b(o=1,e){return l(o,{muted:!1,quality:2,room:e})}function h(o=1){const e=b(o),r=window.open(e,"R58_Program_Output","width=1280,height=720,menubar=no,toolbar=no,location=no,status=no");return r||console.warn("[VDO.ninja] Popup blocked - please allow popups for this site"),r}export{u as V,n as a,m as b,d as c,c as g,h as o};
