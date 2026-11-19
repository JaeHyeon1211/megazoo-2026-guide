#!/usr/bin/env python3
"""메가주 가이드 계산·지도 렌더 회귀 테스트 (브라우저 없이 실행)

    pip install quickjs
    python3 tests/test_logic.py

검사 항목
 1. 2홀 동선 규칙: 세로 통로(출입구에서 가장 가까운 통로) 진입 → 안쪽 끝 → 가로줄로 입구 방향 → 마지막은 입구 쪽 부스
 2. 한 번 지나온 부스는 동선에 두 번 들어가지 않는다(중복 0), 담은 부스는 하나도 빠지지 않는다
 3. 홀 순서는 2 → 3 → 4 → 5 고정
 4. renderMap 회귀: 전체 ↔ 2·3·4·5홀을 전환해도 동선 오버레이(SVG)가 남아 있다
 5. 이벤트 필터: '구매 없이'·'시간 정해진' 판정이 동작한다
"""
import json, re, sys, pathlib

try:
    import quickjs
except ImportError:
    sys.exit('quickjs가 필요합니다: pip install quickjs')

ROOT = pathlib.Path(__file__).resolve().parent.parent

PRELUDE = r"""
var __els = {};
function __mkEl(id){
  if(__els[id]) return __els[id];
  var e = {
    id:id, innerHTML:'', textContent:'', value:'', style:{}, dataset:{}, _cls:{},
    classList:{ add:function(c){e._cls[c]=1;}, remove:function(c){delete e._cls[c];},
      toggle:function(c,v){ if(v===undefined) v=!e._cls[c]; if(v) e._cls[c]=1; else delete e._cls[c]; return !!e._cls[c]; },
      contains:function(c){ return !!e._cls[c]; } },
    addEventListener:function(){}, removeEventListener:function(){},
    querySelectorAll:function(){ return []; }, querySelector:function(){ return null; },
    appendChild:function(){}, insertBefore:function(){}, setAttribute:function(){}, getAttribute:function(){ return null; },
    removeAttribute:function(){}, closest:function(){ return null; },
    getBoundingClientRect:function(){ return {left:0,top:0,width:390,height:520,right:390,bottom:520}; },
    setPointerCapture:function(){}, clientWidth:390, clientHeight:520, offsetHeight:520, offsetWidth:390
  };
  __els[id]=e; return e;
}
var document = { getElementById:function(id){ return __mkEl(id); }, querySelectorAll:function(){ return []; },
  querySelector:function(){ return null; }, addEventListener:function(){},
  createElement:function(){ return __mkEl('tmp'+Math.random()); }, body:__mkEl('body'), documentElement:__mkEl('html') };
var __ls = {};
var localStorage = { getItem:function(k){ return k in __ls ? __ls[k] : null; }, setItem:function(k,v){ __ls[k]=String(v); }, removeItem:function(k){ delete __ls[k]; } };
var navigator = { share:null, clipboard:null };
var location = { hash:'', origin:'http://test.local', pathname:'/index.html', search:'' };
var window = { MZ:null, scrollTo:function(){}, addEventListener:function(){}, matchMedia:function(){ return {matches:false}; } };
var alert = function(){};
"""

TESTS = r"""
var R = window.MZROUTE, T = window.MZTEST, MZ = window.MZ;
var res = {}, fails = [];
function ok(name, cond, extra){ if(!cond) fails.push(name + (extra? ' :: ' + extra : '')); res[name] = !!cond; }

// 1) 2홀 동선 규칙
var h2list = MZ.booths.filter(function(b){ return R.hallKey(b)==='2'; });
var h2 = R.hallRoute(h2list, '2');
var geo = R.HALL_GEO['2'];
var spineCols = [geo.lc, geo.rc];
var cols = h2.map(function(b){ return R.COL_OF[b.id]; });
var rows = h2.map(function(b){ return R.ROW_OF[b.id]; });
var spineN = 0; cols.forEach(function(c){ if(spineCols.indexOf(c)>=0) spineN++; });
ok('2홀 부스 수 보존', h2.length === h2list.length);
ok('2홀 중복 없음', new Set(h2.map(function(b){return b.id;})).size === h2.length);

var contiguous = true, i;
for(i=0;i<h2.length;i++){ var inSp = spineCols.indexOf(cols[i])>=0; if(i<spineN && !inSp) contiguous=false; if(i>=spineN && inSp) contiguous=false; }
ok('세로 통로 부스가 먼저 연속으로 나온다', contiguous);
ok('세로 통로 구간이 비어 있지 않다', spineN > 0);

var mono = true, ys = h2.slice(0,spineN).map(function(b){return b.y;});
for(i=1;i<ys.length;i++){ if(ys[i] > ys[i-1] + 0.01) mono = false; }
ok('세로 진입은 출입문(y큰) → 안쪽(y작은) 순', mono);
ok('세로 진입 첫 부스가 출입문 라인 근처', ys[0] > 800, 'y=' + ys[0]);

var rows2 = rows.slice(spineN), up = true;
for(i=1;i<rows2.length;i++){ if(rows2[i] < rows2[i-1]) up = false; }
ok('가로줄은 안쪽 → 출입문 방향(줄 번호 증가) 순', up);
var maxRow = Math.max.apply(null, h2list.map(function(b){ return R.ROW_OF[b.id]; }));
ok('마지막 부스가 출입문 쪽 마지막 줄', rows[rows.length-1] === maxRow, rows[rows.length-1] + ' vs ' + maxRow);

// 2) 전체 동선
var order = R.routeOrder(MZ.booths);
ok('전체 부스 수 보존', order.length === MZ.booths.length);
ok('전체 중복 없음', new Set(order.map(function(b){return b.id;})).size === order.length);
var seq = []; order.forEach(function(b){ var h = R.hallKey(b); if(!seq.length || seq[seq.length-1]!==h) seq.push(h); });
ok('홀 순서 2→3→4→5', seq.join(',') === '2,3,4,5', seq.join(','));

// 3) renderMap 회귀 — 홀 전환 후에도 동선 오버레이 유지
T.setFavs(['2457','5601','4641','5441']);
T.setView('all');
var ov0 = T.overlayHtml(), vh0 = T.viewHtml();
ok('전체 보기: 동선 오버레이 있음', /polyline/.test(ov0));
ok('전체 보기: 지도 이미지 있음', /map_full\.jpg/.test(vh0));
['2','3','4','5','all'].forEach(function(k){
  T.setView(k);
  var ov = T.overlayHtml(), vh = T.viewHtml();
  ok('홀 전환(' + k + ') 후에도 동선 오버레이 유지', /polyline/.test(ov));
  ok('홀 전환(' + k + ') 후 지도·오버레이 컨테이너 존재', /id="mapsvg"/.test(vh) && /map_h|map_full/.test(vh));
});

// 3-1) 다시 볼 곳이 있어도 배치도 오버레이가 그려진다(되짚는 점선)
T.setRev(['2457']);
T.setView('all');
ok('다시 볼 곳 되짚기 선이 그려진다', /stroke-dasharray/.test(T.overlayHtml()));
T.setView('2');
ok('홀 전환 후에도 되짚기 선 유지', /stroke-dasharray/.test(T.overlayHtml()));
T.setRev([]);

// 4) 내 위치 핀
T.setHere(120, 900);
ok('내 위치 핀 표시', /내 위치/.test(T.overlayHtml()));
ok('내 위치 값 저장', T.getHere() && T.getHere().x === 120);

// 5) 이벤트 필터 판정
var withEv = MZ.booths.filter(function(b){ return b.ev && b.ev.length; });
var nb = withEv.filter(function(b){ return R.evNoBuy(b); });
ok('구매 없이 이벤트가 있는 부스가 있다', nb.length > 20, 'n=' + nb.length);
ok('구매 없이 판정은 구매 조건 문구를 배제', nb.every(function(b){
  return (b.ev||[]).some(function(t){ return !/(구매\s*시|제품\s*구매|결제|구입|원\s*이상)/.test(t); });
}));
var sunday = withEv.filter(function(b){ return R.evTimesFor(b, 0).length; });
ok('일요일 시간 정해진 이벤트 부스가 있다', sunday.length >= 5, 'n=' + sunday.length);
ok('슈퍼벳(2232) 일요일 10·12·14시', JSON.stringify(R.evTimesFor(MZ.booths.filter(function(b){return b.id==='2232';})[0], 0)) === '[600,720,840]');

// 6) 공식 배치도 대조 결과
var b508 = MZ.booths.filter(function(b){return b.id==='5508';})[0];
var b211 = MZ.booths.filter(function(b){return b.id==='3211';})[0];
ok('5508 = 칸나나코리아', b508.label === '칸나나코리아');
ok('3211 = 아이조아 매트', b211.label === '아이조아 매트');
ok('편의시설 데이터 있음', (MZ.fac||[]).length >= 14, 'n=' + (MZ.fac||[]).length);

res.fails = fails;
JSON.stringify(res);
"""

ctx = quickjs.Context()
ctx.eval(PRELUDE)
ctx.eval((ROOT / 'data.js').read_text(encoding='utf-8'))
html = (ROOT / 'index.html').read_text(encoding='utf-8')
script = re.findall(r'<script>(.*?)</script>', html, re.S)[0]
ctx.eval(script)
out = json.loads(ctx.eval(TESTS))
fails = out.pop('fails')
for k, v in out.items():
    print(('PASS ' if v else 'FAIL ') + k)
if fails:
    print('\nFAILED:'); [print(' - ' + f) for f in fails]
    sys.exit(1)
print('\n모든 검사 통과 (%d개)' % len(out))
