// The server keeps the database. This public file contains no passwords or API keys.
const API='https://biblioteca-carolina-sgb.leaflesscrown1.chatgpt.site/api/library';
const KEY='sgb-session';
export async function apiFetch(_path:string,options:RequestInit={}){
 const headers=new Headers(options.headers);
 const token=sessionStorage.getItem(KEY);
 if(token)headers.set('Authorization','Bearer '+token);
 const response=await fetch(API,{...options,headers,credentials:'omit'});
 const nextToken=response.headers.get('X-Session-Token');
 if(response.ok&&nextToken)sessionStorage.setItem(KEY,nextToken);
 if(response.status===401)sessionStorage.removeItem(KEY);
 if(response.ok&&typeof options.body==='string'){
  try{if(JSON.parse(options.body).action==='logout')sessionStorage.removeItem(KEY);}catch{}
 }
 return response;
}
