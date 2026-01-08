const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["assets/index-KRz20TQu.js","assets/index-DweTpE8z.css"])))=>i.map(i=>d[i]);
import{N as h}from"./index-KRz20TQu.js";let s=null;async function i(){if(s)return s;try{const{getDeviceUrl:o}=await h(async()=>{const{getDeviceUrl:r}=await import("./index-KRz20TQu.js").then(e=>e.a3);return{getDeviceUrl:r}},__vite__mapDeps([0,1])),a=o();if(a){const r=new AbortController,e=setTimeout(()=>r.abort(),3e3),n=await fetch(`${a}/api/config`,{signal:r.signal,mode:"cors",cache:"no-cache"});if(clearTimeout(e),n.ok){const c=await n.json();if(c.vdo_host||c.vdoninja_host)return s=c.vdo_host||c.vdoninja_host,s}}}catch{console.log("[VDO.ninja] Device does not provide VDO.ninja host configuration")}const t="r58-vdo.itagenten.no";return s=t,console.log(`[VDO.ninja] Using default host: ${t}`),t}function u(){return"https"}const l="studio",b="preke-r58-2024";function d(){var o,a;const t=`
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
`;if(typeof window<"u"&&((a=(o=window.location)==null?void 0:o.origin)!=null&&a.startsWith("file://")))return"";try{return"b64:"+btoa(unescape(encodeURIComponent(t)))}catch{return""}}async function p(t){const o=await i();if(!o)return null;const a=u(),r=new URL(`${a}://${o}/`);return r.searchParams.set("scene",""),r.searchParams.set("room",l),r.searchParams.set("cover",""),r.searchParams.set("quality","2"),r.searchParams.set("cleanoutput",""),r.searchParams.set("hideheader",""),r.searchParams.set("nologo",""),r.searchParams.set("whipout",t),r.searchParams.set("autostart",""),r.searchParams.set("videodevice","0"),r.searchParams.set("audiodevice","0"),r.searchParams.set("css",d()),r.toString()}async function g(t,o={}){const a=await i();if(!a)return null;const r=u(),e=new URL(`${r}://${a}/`);e.searchParams.set("scene",t.toString()),e.searchParams.set("room",o.room||l),e.searchParams.set("password",b),e.searchParams.set("cover",""),e.searchParams.set("cleanoutput",""),e.searchParams.set("hideheader",""),e.searchParams.set("nologo",""),e.searchParams.set("quality",(o.quality??2).toString()),o.muted&&e.searchParams.set("muted","");const n=d();return n&&e.searchParams.set("css",n),e.toString()}async function m(t=1,o){return g(t,{muted:!1,quality:2,room:o})}async function P(t=1){const o=await m(t);if(!o)return console.warn("[VDO.ninja] Cannot open popup - VDO.ninja not configured"),null;const r=window.open(o,"R58_Program_Output","width=1280,height=720,menubar=no,toolbar=no,location=no,status=no");return r||console.warn("[VDO.ninja] Popup blocked - please allow popups for this site"),r}export{l as V,u as a,p as b,b as c,i as g,P as o};
