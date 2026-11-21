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
var setTimeout = function(fn, ms){ return 0; };
var clearTimeout = function(){ };
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

// 7) 거리 환산 근거(2026-11-19 재계산) — 화면의 거리·시각은 이 상수로만 계산된다
var W_PT = 3215.29, H_PT = 2267.72;            // 배치도 PDF 1페이지(pt)
var M_PER_XUNIT = R.UNIT_M;                     // x 1단위 = 0.260m
var M_PER_PT_X = M_PER_XUNIT * 1000 / W_PT;     // 가로: 252m / 3115.0pt = 0.08090
ok('가로 1,000단위 ≈ 260m', Math.abs(M_PER_XUNIT*1000 - 260) <= 0.5, 'm=' + (M_PER_XUNIT*1000));
ok('환산하면 표준 1부스 폭 37.1pt = 3.0m', Math.abs(37.1*M_PER_PT_X - 3.0) < 0.02, 'm=' + (37.1*M_PER_PT_X).toFixed(3));
ok('2홀↔ 5홀 출입구 간격 ≈ 189m(홀 3개 폭)', Math.abs((R.GATES['5']-R.GATES['2'])*M_PER_XUNIT - 189) < 6, 'm=' + ((R.GATES['5']-R.GATES['2'])*M_PER_XUNIT).toFixed(1));
ok('세로 보정은 0.70~0.75', R.YCORR > 0.70 && R.YCORR < 0.75, 'k=' + R.YCORR);
ok('세로 1,000단위 ≈ 191m (171m/2032.4pt 기준)', Math.abs(R.dist({x:0,y:0},{x:0,y:1000})*M_PER_XUNIT - 190.8) < 1.5, 'm=' + (R.dist({x:0,y:0},{x:0,y:1000})*M_PER_XUNIT).toFixed(1));
ok('가로 이동만 있을 때 직선거리 = 좌표 차이 그대로', Math.abs(R.dist({x:0,y:0},{x:1000,y:0}) - 1000) < 1e-6);

// 8) 화면 표기 — 거리는 '도면 직선거리 환산 참고치'로, 사람 화장실은 미확인으로 분리
T.setFavs(['2457','5601','4641','5441']);
T.goTab('course');
var courseHtml = T.viewHtml();
ok('내 코스: 도면 직선거리 참고치 라벨', /도면 직선거리/.test(courseHtml) && /참고치/.test(courseHtml));
ok('내 코스: 대기·구매시간 미포함 명시', /구매시간은 빠져/.test(courseHtml));
ok('내 코스: 예전 166m 표기 없음', !/166\s*m/.test(courseHtml));
ok('내 코스: 도면 1,000 ≈ 260m 근거 표기', /1,000\s*\u2248\s*260m/.test(courseHtml));
T.setFavs(['2232','2457']);
T.goTab('course');
var courseAnchor = T.viewHtml();
ok('정시 이벤트를 담으면 시간순 우선 배치·교차 가능 문구', /시간순 우선 배치/.test(courseAnchor) && /교차/.test(courseAnchor));
T.setView('all');
var infoHtml = T.viewHtml();
var infoText = infoHtml.replace(/<[^>]+>/g,' ');
ok('안내: 사람 화장실 위치 미확인 분리', /사람 화장실[\s\S]{0,80}위치 미확인/.test(infoText));
ok('안내: 킨텍스 공식 시설안내 링크·확인일', /kintex\.com\/web\/ko\/service\/facilities2\.do/.test(infoHtml) && /2026-11-19 확인/.test(infoHtml));
ok('안내: 유아휴게실·4홀·공식 사무번호', /유아휴게실[\s\S]{0,40}4홀 부근/.test(infoHtml) && /031-995-8114/.test(infoHtml) && /031-995-8233/.test(infoHtml));
ok('안내: 옛 사무번호(031-810) 없음', !/031-810/.test(infoHtml));

// 9) 꼭 사야 될 리스트 — 품목별 목록 (2026-11-22 슬랙 #메가주 요청)
var G = R.CORE_GROUPS;
ok('품목 그룹 11개', G.length === 11, 'n=' + G.length);
var allItems = [];
G.forEach(function(g){ R.CORE.forEach(function(c){ if(c.grp.indexOf(g.key)>=0) allItems.push(c.id); }); });
ok('품목별 합계 = 필수부스 69 + 겹침 9', allItems.length === 78, 'n=' + allItems.length);
ok('필수부스 중복 없는 69곳', new Set(R.CORE.map(function(c){return c.id;})).size === 69);

T.setFavs([]); T.setDone([]);
T.setCourseView('item');
var iv = T.viewHtml();
ok('품목별 보기 전환 버튼(두 보기 모두)', /data-cview="item"/.test(iv) && /data-cview="order"/.test(iv));
ok('품목별 보기 제목', /꼭 사야 될 리스트/.test(iv));
ok('품목 칩 13개(전체·찜 + 품목 11)', (iv.match(/data-ichip=/g)||[]).length === 13, 'n=' + (iv.match(/data-ichip=/g)||[]).length);
ok('전체 보기: 품목 덩어리 11개', (iv.match(/class="igrp/g)||[]).length === 11, 'n=' + (iv.match(/class="igrp/g)||[]).length);
ok('전체 보기: 접힌 품목은 부스번호를 미리 보여 준다', /class="iprev"/.test(iv));

var ROW = function(h){ return (h.match(/data-ifav="([^"]+)"/g)||[]).map(function(s){ return s.slice(11, -1); }); };
var secMiss = [], secDup = [], secCnt = true, secOrder = true, secHall = true;
G.forEach(function(g){
  T.setItemSel(g.key);
  var h = T.viewHtml();
  var got = ROW(h);
  var want = R.CORE.filter(function(c){ return c.grp.indexOf(g.key)>=0; }).map(function(c){return c.id;});
  if(got.length !== want.length) secCnt = false;
  if(new Set(got).size !== got.length) secDup.push(g.key);
  want.forEach(function(id){ if(got.indexOf(id)<0) secMiss.push(g.key + ':' + id); });
  var exp = R.routeOrder(MZ.booths.filter(function(b){ return got.indexOf(b.id)>=0; })).map(function(b){return b.id;});
  if(got.join(',') !== exp.join(',')) secOrder = false;
  if(!/(2|3|4|5)홀|경기도 공동관|ART존/.test(h)) secHall = false;
});
ok('품목을 고르면 그 품목 부스가 모두 나온다', secCnt, secMiss.join(','));
ok('품목 안 부스 중복 없음', secDup.length === 0, secDup.join(','));
ok('품목 안에서 2홀 입구 동선 순서', secOrder);
ok('부스 줄에 홀 표기', secHall);
var seenIds = {};
G.forEach(function(g){ T.setItemSel(g.key); ROW(T.viewHtml()).forEach(function(id){ seenIds[id] = 1; }); });
ok('품목별 목록에 필수부스 69곳이 모두 나온다', Object.keys(seenIds).length === 69, 'n=' + Object.keys(seenIds).length);

T.setFavs(['2457','5601','4641']); T.setDone(['2457']);
T.setItemSel('eye');
var eh = T.viewHtml();
ok('담김·방문 상태가 줄에 표시', /★ 담김/.test(eh) && /✓ 방문함/.test(eh));
ok('품목 머리에 담김 수 요약', /담김 1/.test(eh));
ok('줄마다 방문 체크·지도 버튼', (eh.match(/data-idone=/g)||[]).length > 0 && (eh.match(/data-imap=/g)||[]).length > 0);
ok('확인 포인트 버튼', /data-ick="2457"/.test(eh));

T.setItemSel('all');
var ah = T.viewHtml();
ok('품목 밖 직접 찜한 부스 섬션', /직접 찜한 부스/.test(ah) && ah.indexOf('5601') >= 0);
T.setItemSel('fav');
var fh = T.viewHtml();
ok('찜한 부스만 보기', /찜한 부스 \(동선 순서\)/.test(fh) && ROW(fh).length === 3, 'n=' + ROW(fh).length);

T.setCourseView('order');
var ov2 = T.viewHtml();
ok('방문 순서 보기에도 보기 전환 버튼', /data-cview="order"/.test(ov2) && /data-cview="item"/.test(ov2));
ok('방문 순서 보기·필수품목 상자 그대로', /id="coretoggle"/.test(ov2) && /class="step/.test(ov2));

T.clearFocus();
T.focusBooth('5601');
var fov = T.overlayHtml();
ok('품목 목록 지도 버튼: 강조 부스 저장', T.getFocus() === '5601');
ok('품목 목록 지도 버튼: 배치도에 빨간 테두리', /stroke-width="3.4"/.test(fov));
ok('배치도에 「표시 끄기」 칩', /id="focusclr"/.test(T.viewHtml()) && /5601/.test(T.viewHtml()));
ok('강조 부스 번호 라벨', /5601/.test(fov));
T.clearFocus();
ok('표시 끄면 강조가 사라진다', !/stroke-width="3.4"/.test(T.overlayHtml()));
T.setItemSel('all'); T.setDone([]); T.setFavs([]);

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
