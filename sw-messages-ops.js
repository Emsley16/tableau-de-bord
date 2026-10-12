/* Messages ops — réseau d'abord, cache en secours (fonctionnement hors ligne) */
const C="messages-ops-v1";
self.addEventListener("install",e=>{self.skipWaiting();});
self.addEventListener("activate",e=>{e.waitUntil(self.clients.claim());});
self.addEventListener("fetch",e=>{
  const r=e.request;
  if(r.method!=="GET")return;
  const u=new URL(r.url);
  if(u.origin!==self.location.origin)return;
  e.respondWith(
    fetch(r,{cache:"no-store"}).then(res=>{
      if(res&&res.ok){const cp=res.clone();caches.open(C).then(c=>c.put(r,cp));}
      return res;
    }).catch(()=>caches.match(r,{ignoreSearch:true}).then(m=>m||caches.match("./messages-ops.html")))
  );
});
