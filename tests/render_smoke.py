#!/usr/bin/env python3
"""탭별 렌더 스모크 테스트 — 모든 탭을 실제로 그려 보고 오류·분량을 확인한다.

    python3 tests/render_smoke.py
"""
import json, re, pathlib, sys
try:
    import quickjs
except ImportError:
    sys.exit('quickjs가 필요합니다: pip install quickjs')

ROOT = pathlib.Path(__file__).resolve().parent.parent
src = (ROOT / 'tests' / 'test_logic.py').read_text(encoding='utf-8')
PRELUDE = re.search(r'PRELUDE = r"""(.*?)"""', src, re.S).group(1)

ctx = quickjs.Context()
ctx.eval(PRELUDE)
ctx.eval((ROOT / 'data.js').read_text(encoding='utf-8'))
html = (ROOT / 'index.html').read_text(encoding='utf-8')
ctx.eval(re.findall(r'<script>(.*?)</script>', html, re.S)[0])

CODE = r"""
var T = window.MZTEST, out = {};
try { T.goTab('booth'); var h = T.viewHtml();
  var lb = document.getElementById('list');
  out.boothLen = h.length;
  out.boothCards = (lb.innerHTML.match(/class="card/g)||[]).length;
  out.boothMore = /id="morebooth"/.test(lb.innerHTML);
  out.boothDescFold = (lb.innerHTML.match(/data-desc=/g)||[]).length;
  out.cntText = document.getElementById('cnt').textContent;
} catch(e){ out.boothErr = String(e); }
try { T.goTab('event'); out.eventLen = T.viewHtml().length; } catch(e){ out.eventErr = String(e); }
try { T.goTab('price'); var p = T.viewHtml(); out.priceLen = p.length;
  out.priceRows = (p.match(/class="pcard"/g)||[]).length;
  out.priceFold = /id="ckbody" class="fold"/.test(p) || /class="fold" id="ckbody"/.test(p);
} catch(e){ out.priceErr = String(e); }
try { T.goTab('info'); var i = T.viewHtml(); out.infoLen = i.length;
  out.infoFolds = (i.match(/class="fold"/g)||[]).length;
} catch(e){ out.infoErr = String(e); }
try { T.setFavs(['2457','5601','4641','5441']); T.goTab('course'); var c = T.viewHtml();
  out.courseLen = c.length;
  out.courseCoreFolded = /id="coretoggle"/.test(c);
  out.courseRouteAfterCore = c.indexOf('class="step') > 0 && c.indexOf('class="step') < c.indexOf('id="coretoggle"');
} catch(e){ out.courseErr = String(e); }
// 품목별 목록 보기(2026-11-22) — 보기를 바꿔도 오류 없이 그려지고 줄이 나온다
try { T.setCourseView('item'); var it = T.viewHtml();
  out.itemLen = it.length;
  out.itemChips = (it.match(/data-ichip=/g)||[]).length;
  out.itemSections = (it.match(/class="igrp/g)||[]).length;
  T.setItemSel('probio'); var ip = T.viewHtml();
  out.itemProbioRows = (ip.match(/data-ifav=/g)||[]).length;
  out.itemHasMapBtn = /data-imap=/.test(ip);
  T.setItemSel('all'); T.setCourseView('order');
} catch(e){ out.itemErr = String(e); }
JSON.stringify(out);
"""
res = json.loads(ctx.eval(CODE))
for k, v in res.items():
    print(k, '=', v)
errs = {k: v for k, v in res.items() if k.endswith('Err')}
if errs:
    sys.exit('렌더 오류: %s' % errs)
print('\n모든 탭 렌더 OK')
