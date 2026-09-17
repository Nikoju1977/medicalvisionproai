from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

loader = '<script src="web-knowledge.js"></script>\n<script src="web-knowledge-ui.js"></script>'
if 'src="web-knowledge.js"' not in s:
    if '</body>' not in s:
        raise SystemExit('cannot inject web knowledge loader: </body> not found')
    s = s.replace('</body>', loader + '\n</body>', 1)

required = ['src="web-knowledge.js"', 'src="web-knowledge-ui.js"']
missing = [x for x in required if x not in s]
if missing:
    raise SystemExit('web knowledge loader incomplete: ' + ', '.join(missing))

p.write_text(s, encoding='utf-8')
print('Web knowledge loader injected into index.html')
