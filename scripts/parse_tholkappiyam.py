import sys, re, csv, html

src, out = sys.argv[1], sys.argv[2]
lines = open(src, encoding='utf-8').read().split('\n')

ATIKARAM = {'0': 'சிறப்புப் பாயிரம்', '1': 'எழுத்ததிகாரம்', '2': 'சொல்லதிகாரம்', '3': 'பொருளதிகாரம்'}

re_iyal = re.compile(r'<strong>\s*(\d)\.\s*(\d)\.\s*(.*?)\s*</strong>')
re_payiram = re.compile(r'<h3>\s*$')
re_num = re.compile(r'^(.*?)[\t ]*(\d+)\s*(?:<br>)+\s*$')

rows = []
cur_atik = cur_iyal = None
in_body = False
buf = []
warnings = []

def flush(num):
    global buf
    text = '\n'.join(buf).strip()
    buf = []
    if not text:
        warnings.append(f'empty poem {cur_atik}/{cur_iyal} #{num}')
    rows.append([cur_atik, cur_iyal, int(num), text])

def clean(s):
    s = re.sub(r'<br\s*/?>', '', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s).replace('‎', '')
    return s.strip()

i = 0
while i < len(lines):
    line = lines[i]
    # Payiram header: <center><h3>\nதொல்காப்பியம் -சிறப்புப்பாயிரம்</h3>
    if '<h3>' in line and i + 1 < len(lines) and 'சிறப்புப்பாயிரம்' in lines[i+1]:
        cur_atik = ATIKARAM['0']; cur_iyal = 'சிறப்புப் பாயிரம்'; in_body = True; buf = []
        i += 2; continue
    m = re_iyal.search(line)
    if m:
        cur_atik = ATIKARAM[m.group(1)]; cur_iyal = clean(m.group(3)); in_body = True; buf = []
        i += 1; continue
    if 'முற்றிற்று' in line:
        in_body = False
    if in_body:
        if line.startswith('<center>') or line.startswith('<strong>') or re.match(r'^\s*-{3,}', line) or '</h3>' in line:
            i += 1; continue
        m = re_num.match(line)
        if cur_atik == ATIKARAM['0']:
            # payiram: trailing 5/10/15 are line markers of a single poem
            t = clean(m.group(1)) if m else clean(line)
            if t: buf.append(t)
            if i + 1 < len(lines) and lines[i+1].startswith('----'):
                flush('1')
        elif m:
            t = clean(m.group(1))
            if t: buf.append(t)
            flush(m.group(2))
        else:
            t = clean(line)
            if t: buf.append(t)
    i += 1

# sequence check
from itertools import groupby
for (a, iy), grp in groupby(rows, key=lambda r: (r[0], r[1])):
    nums = [r[2] for r in grp]
    exp = list(range(1, len(nums) + 1))
    if nums != exp:
        warnings.append(f'{a}/{iy}: non-sequential {nums[:5]}... count={len(nums)} max={max(nums)}')

with open(out, 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f)
    w.writerow(['அதிகாரம்', 'இயல்', 'பாடல் எண்', 'பாடல்'])
    w.writerows(rows)

print(f'rows: {len(rows)}')
for (a, iy), grp in groupby(rows, key=lambda r: (r[0], r[1])):
    print(f'  {a} / {iy}: {len(list(grp))}')
print('WARNINGS:' if warnings else 'no warnings')
for w_ in warnings: print(' ', w_)
