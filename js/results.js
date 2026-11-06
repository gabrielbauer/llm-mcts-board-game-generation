(function(){
'use strict';
var D=window.RESULTS, NS='http://www.w3.org/2000/svg';
var MODELS=['DeepSeek-V4-Pro','Claude-Sonnet-5','GPT-5','Qwen3.6-Plus'];
var COL={'DeepSeek-V4-Pro':'#2a78d6','Claude-Sonnet-5':'#eb6834','GPT-5':'#1baf7a','Qwen3.6-Plus':'#eda100'};
var INK='#14202E',GRAY='#4A5B6D',LINE='#D5E0EB',NAVY='#0B2545',TEAL='#0B7A75';
function el(tag,attrs,parent){var e=document.createElementNS(NS,tag);for(var k in attrs)e.setAttribute(k,attrs[k]);if(parent)parent.appendChild(e);return e}
function txt(parent,x,y,s,attrs){var t=el('text',Object.assign({x:x,y:y,fill:GRAY,'font-size':12.5},attrs||{}),parent);t.textContent=s;return t}
function f3(v){return v==null?'—':v.toFixed(3)} function f2(v){return v==null?'undefined':v.toFixed(2)}
// ---------- tooltip
var tip=document.createElement('div');tip.className='tip';tip.setAttribute('role','status');document.body.appendChild(tip);
function showTip(x,y,build){tip.textContent='';build(tip);tip.classList.add('show');
  var r=tip.getBoundingClientRect(),vw=window.innerWidth,vh=window.innerHeight;
  var L=x+14,T=y+14; if(L+r.width>vw-8)L=x-r.width-14; if(L<8)L=8; if(T+r.height>vh-8)T=y-r.height-14; if(T<8)T=8;
  tip.style.left=L+'px';tip.style.top=T+'px'}
function hideTip(){tip.classList.remove('show')}
function line(p,cls,s){var d=document.createElement('div');d.className=cls||'row';if(s!=null)d.textContent=s;p.appendChild(d);return d}
function keyRow(p,color,label,value,extra){var r=line(p,'row');if(color){var k=document.createElement('span');k.className='key';k.style.background=color;r.appendChild(k)}
  var st=document.createElement('strong');st.textContent=value;r.appendChild(st);var sp=document.createElement('span');sp.textContent=' '+label;r.appendChild(sp);
  if(extra){var m=document.createElement('span');m.className='mut';m.textContent=extra;r.appendChild(m)}return r}
function ptr(e){return e.touches&&e.touches[0]?{x:e.touches[0].clientX,y:e.touches[0].clientY}:{x:e.clientX,y:e.clientY}}
// ---------- frame
function frame(host,opt){
  host.textContent='';var W=Math.max(300,host.clientWidth),H=opt.h||(W<560?250:300);
  var m={l:50,r:16,t:14,b:44};var svg=el('svg',{viewBox:'0 0 '+W+' '+H,width:W,height:H},host);
  var iw=W-m.l-m.r,ih=H-m.t-m.b;
  var X=function(v){return m.l+(v-opt.x0)/(opt.x1-opt.x0)*iw},Y=function(v){return m.t+(1-v)*ih};
  var g=el('g',{},svg);
  [0,0.25,0.5,0.75,1].forEach(function(v){el('line',{x1:m.l,x2:W-m.r,y1:Y(v),y2:Y(v),stroke:LINE,'stroke-width':v===0?1.2:0.8},g);
    txt(g,m.l-8,Y(v)+4,v===0?'0':v===1?'1':String(v),{'text-anchor':'end'})});
  for(var i=opt.x0;i<=opt.x1;i++)txt(g,X(i),H-m.b+18,String(i),{'text-anchor':'middle'});
  txt(g,m.l+iw/2,H-6,opt.xl,{'text-anchor':'middle','font-size':12.5});
  var yl=txt(g,0,0,'Fitness',{'text-anchor':'middle',transform:'translate(13 '+(m.t+ih/2)+') rotate(-90)'});
  return {svg:svg,X:X,Y:Y,W:W,H:H,m:m,iw:iw,ih:ih}
}
// ---------- mean chart (crosshair)
function meanChart(host){
  var G=D.mean.length-1,F=frame(host,{x0:0,x1:G,xl:'Generation (0 = first draft)'}),X=F.X,Y=F.Y,svg=F.svg;
  var up=D.q.map(function(q,i){return X(i)+','+Y(q[2])}).join(' '),dn=D.q.map(function(q,i){return X(i)+','+Y(q[0])}).reverse().join(' ');
  el('polygon',{points:up+' '+dn,fill:'#0B7A75','fill-opacity':0.13},svg);
  el('polyline',{points:D.mean.map(function(v,i){return X(i)+','+Y(v)}).join(' '),fill:'none',stroke:NAVY,'stroke-width':2.5,'stroke-linejoin':'round'},svg);
  D.mean.forEach(function(v,i){el('circle',{cx:X(i),cy:Y(v),r:4.5,fill:NAVY,stroke:'#fff','stroke-width':2},svg)});
  txt(svg,X(G)-4,Y(D.q[G][2])-8,'interquartile range',{'text-anchor':'end',fill:TEAL});
  txt(svg,X(1.15),Y(D.mean[1])+24,'mean of 16 runs',{fill:NAVY,'font-weight':600});
  var cross=el('line',{y1:F.m.t,y2:F.H-F.m.b,stroke:INK,'stroke-width':1,'stroke-dasharray':'3 3',opacity:0},svg);
  var dot=el('circle',{r:7,fill:'none',stroke:NAVY,'stroke-width':2,opacity:0},svg);
  var hit=el('rect',{x:F.m.l-10,y:F.m.t,width:F.iw+20,height:F.ih,fill:'transparent'},svg);
  function move(e){var p=ptr(e),r=svg.getBoundingClientRect(),sx=(p.x-r.left)*F.W/r.width;
    var i=Math.round((sx-F.m.l)/F.iw*G);i=Math.max(0,Math.min(G,i));
    cross.setAttribute('x1',X(i));cross.setAttribute('x2',X(i));cross.setAttribute('opacity',1);
    dot.setAttribute('cx',X(i));dot.setAttribute('cy',Y(D.mean[i]));dot.setAttribute('opacity',1);
    var q=D.q[i];showTip(p.x,p.y,function(t){line(t,'tt',i===0?'Generation 0 (first draft)':'Generation '+i);
      keyRow(t,NAVY,'mean',f3(D.mean[i]));keyRow(t,null,'median',f3(q[1]));keyRow(t,null,'middle half of runs',f3(q[0])+'–'+f3(q[2]))})}
  function out(){cross.setAttribute('opacity',0);dot.setAttribute('opacity',0);hideTip()}
  hit.addEventListener('pointermove',move);hit.addEventListener('pointerdown',move);hit.addEventListener('pointerleave',out);
}
// ---------- per-game charts
var pinned=null,hover=null,gameHosts=[];
function applyHL(){var m=hover||pinned;
  gameHosts.forEach(function(h){var s=h.querySelector('svg');if(!s)return;s.classList.toggle('hl',!!m);
    s.querySelectorAll('.series').forEach(function(g){g.classList.toggle('on',g.getAttribute('data-m')===m)})});
  document.querySelectorAll('.chip').forEach(function(c){c.setAttribute('aria-pressed',String(c.getAttribute('data-m')===pinned))})}
function gameChart(host){
  var gid=host.getAttribute('data-g'),runs=D.runs.filter(function(r){return r.g===gid});
  var N=Math.max.apply(null,runs.map(function(r){return r.c.length}));
  var F=frame(host,{x0:0,x1:N-1,xl:'Generation (0 = first draft)'}),X=F.X,Y=F.Y,svg=F.svg;
  MODELS.forEach(function(mn){var r=runs.filter(function(x){return x.m===mn})[0];if(!r)return;var c=COL[mn];
    var g=el('g',{'class':'series','data-m':mn},svg);
    var inc=r.c[0][1],path='M'+X(0)+' '+Y(inc),prev=inc;
    r.c.forEach(function(p,k){if(k===0)return;var x=X(k);
      el('line',{x1:X(k-1),y1:Y(prev),x2:x,y2:Y(p[1]),stroke:c,'stroke-width':1.6,'stroke-dasharray':'2 3'},g);
      if(p[2]){path+=' H'+x+' V'+Y(p[1]);prev=p[1]}else{path+=' H'+x}});
    el('path',{d:path,fill:'none',stroke:c,'stroke-width':2.5,'stroke-linejoin':'round'},g);
    el('path',{d:path,fill:'none',stroke:'transparent','stroke-width':14,'data-hit':'1'},g).addEventListener('pointerenter',function(){hover=mn;applyHL()});
    r.c.forEach(function(p,k){var x=X(k),y=Y(p[1]);
      if(p[2])el('circle',{cx:x,cy:y,r:4.5,fill:c,stroke:'#fff','stroke-width':2},g);
      else{var s=5;el('path',{d:'M'+(x-s)+' '+(y-s)+'L'+(x+s)+' '+(y+s)+'M'+(x+s)+' '+(y-s)+'L'+(x-s)+' '+(y+s),stroke:'#fff','stroke-width':5,'stroke-linecap':'round'},g);
        el('path',{d:'M'+(x-s)+' '+(y-s)+'L'+(x+s)+' '+(y+s)+'M'+(x+s)+' '+(y-s)+'L'+(x-s)+' '+(y+s),stroke:c,'stroke-width':2.4,'stroke-linecap':'round'},g)}
      var h=el('circle',{cx:x,cy:y,r:12,fill:'transparent',tabindex:0},g);
      function on(e){hover=mn;applyHL();var pp=e&&e.clientX!=null?ptr(e):(function(){var b=h.getBoundingClientRect();return{x:b.right,y:b.top}})();
        showTip(pp.x,pp.y,function(t){line(t,'tt',mn+' · '+gid);
          keyRow(t,c,k===0?'first draft (generation 0)':'generation '+k,f3(p[1]),k===0?'':(p[2]?' · kept':' · rejected'));
          line(t,'row mut','Completion '+f2(p[3])+' · Balance '+f2(p[4]));line(t,'row mut','Agency '+f2(p[5])+' · Coverage '+f2(p[6]))})}
      function off(){hover=null;applyHL();hideTip()}
      h.addEventListener('pointerenter',on);h.addEventListener('pointerdown',on);h.addEventListener('pointerleave',off);h.addEventListener('focus',on);h.addEventListener('blur',off)});
    g.addEventListener('pointerleave',function(){hover=null;applyHL()});
  });
  applyHL();
}
function dataTable(host){var gid=host.getAttribute('data-table');var t=document.createElement('table');
  var hd=t.createTHead().insertRow();['Model','Gen.','Fitness','Kept','Compl.','Balance','Agency','Coverage'].forEach(function(s){var th=document.createElement('th');th.textContent=s;hd.appendChild(th)});
  var b=t.createTBody();D.runs.filter(function(r){return r.g===gid}).forEach(function(r){r.c.forEach(function(p,k){var tr=b.insertRow();
    [r.m,String(k),f3(p[1]),k===0?'first draft':(p[2]?'yes':'no'),f2(p[3]),f2(p[4]),f2(p[5]),f2(p[6])].forEach(function(s){tr.insertCell().textContent=s})})});
  host.appendChild(t)}
// ---------- chips
function chips(){var box=document.getElementById('chips');if(!box)return;
  MODELS.forEach(function(mn){var b=document.createElement('button');b.type='button';b.className='chip';b.setAttribute('data-m',mn);b.setAttribute('aria-pressed','false');
    var i=document.createElement('i');i.style.setProperty('--c',COL[mn]);b.appendChild(i);b.appendChild(document.createTextNode(mn));
    b.addEventListener('pointerenter',function(){hover=mn;applyHL()});b.addEventListener('pointerleave',function(){hover=null;applyHL()});
    b.addEventListener('click',function(){pinned=pinned===mn?null:mn;applyHL()});box.appendChild(b)})}
// ---------- table + bars hover
function table(){var t=document.getElementById('fit');if(!t)return;
  t.querySelectorAll('td[data-v]').forEach(function(td){
    function on(e){var c=td.getAttribute('data-c'),tr=td.parentNode;t.classList.add('hl');
      t.querySelectorAll('td[data-v]').forEach(function(x){x.classList.toggle('on',x.parentNode===tr||x.getAttribute('data-c')===c)});
      t.querySelectorAll('thead th').forEach(function(x){x.classList.toggle('on',x.getAttribute('data-c')===c)});
      var m=td.getAttribute('data-m'),g=td.getAttribute('data-g'),v=td.getAttribute('data-v');
      var pp=e&&e.clientX!=null?ptr(e):(function(){var r=td.getBoundingClientRect();return{x:r.right,y:r.top}})();
      showTip(pp.x,pp.y,function(tp){
        if(g==='Mean'){line(tp,'tt',m);keyRow(tp,null,'mean over the 4 games',v)}
        else if(m==='Mean'){line(tp,'tt',g);keyRow(tp,null,'mean over the 4 models',v)}
        else{var r=D.runs.filter(function(x){return x.g===g&&x.m===m})[0];line(tp,'tt',m+' · '+g);keyRow(tp,COL[m],'best game',v);
          if(r){keyRow(tp,null,'first draft',f3(r.c[0][1]));line(tp,'row mut',r.c.length+' candidates')}}})}
    function off(){t.classList.remove('hl');t.querySelectorAll('.on').forEach(function(x){x.classList.remove('on')});hideTip()}
    td.addEventListener('pointerenter',on);td.addEventListener('pointermove',on);td.addEventListener('pointerleave',off);td.addEventListener('focus',on);td.addEventListener('blur',off)})}
function bars(){var b=document.getElementById('bars');if(!b)return;
  b.querySelectorAll('.bar-row').forEach(function(r){
    function on(e){b.classList.add('hl');b.querySelectorAll('.bar-row').forEach(function(x){x.classList.toggle('on',x===r)});
      var m=r.getAttribute('data-m'),f0=+r.getAttribute('data-f0'),f1=+r.getAttribute('data-f1');
      var pp=e&&e.clientX!=null?ptr(e):(function(){var q=r.getBoundingClientRect();return{x:q.right-40,y:q.top}})();
      showTip(pp.x,pp.y,function(t){line(t,'tt',m);keyRow(t,'#B9C7D4','first draft',f3(f0));keyRow(t,TEAL,'best after the loop',f3(f1));line(t,'row mut','+'+(f1-f0).toFixed(3)+' (mean of 4 games)')})}
    function off(){b.classList.remove('hl');r.classList.remove('on');hideTip()}
    r.addEventListener('pointerenter',on);r.addEventListener('pointermove',on);r.addEventListener('pointerleave',off);r.addEventListener('focus',on);r.addEventListener('blur',off)})}
// ---------- init + resize
function render(){document.querySelectorAll('[data-chart=mean]').forEach(meanChart);
  gameHosts=[].slice.call(document.querySelectorAll('[data-chart=game]'));gameHosts.forEach(gameChart)}
chips();render();table();bars();
document.querySelectorAll('[data-table]').forEach(dataTable);
var rw=null,lastW=window.innerWidth;window.addEventListener('resize',function(){if(window.innerWidth===lastW)return;lastW=window.innerWidth;clearTimeout(rw);rw=setTimeout(render,150)});
document.addEventListener('scroll',hideTip,{passive:true});
})();
