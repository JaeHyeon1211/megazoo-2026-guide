import base64, os

html = open('index.html', encoding='utf-8').read()
data = open('data.js', encoding='utf-8').read()
html = html.replace('<script src="data.js"></script>', '<script>' + data + '</script>')

imgs = ['map_full.jpg', 'map_h2.jpg', 'map_h3.jpg', 'map_h4.jpg', 'map_h5.jpg']
for key in imgs:
    b64 = base64.b64encode(open(key, 'rb').read()).decode()
    html = html.replace('src="%s"' % key, 'src="data:image/jpeg;base64,%s"' % b64)

# 이미지 경로가 여러 곳(지도 뷰 전환)에서 쓰이므로 MZIMG 맵도 함께 넣는다
imgs_js = 'window.MZIMG={' + ','.join('"%s":"data:image/jpeg;base64,%s"' % (k, base64.b64encode(open(k, 'rb').read()).decode()) for k in imgs) + '};'
html = html.replace('<script>', '<script>' + imgs_js + '</script><script>', 1)
open('standalone.html', 'w', encoding='utf-8').write(html)
print('standalone.html', round(os.path.getsize('standalone.html') / 1024), 'KB')
