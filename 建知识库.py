# -*- coding: utf-8 -*-
"""从现有课程材料里抽出知识库 —— 助教小莉的地基

    python 建知识库.py

读三样东西：
    发给学生/第1周-让电脑说话/使用说明.txt        报错清单（通用）
    发给学生/第1周-让电脑说话/Mac版安装说明.txt    报错清单（Mac）+ 安装步骤
    题库/计算思维-第1章-题库.docx                 49 题，取知识点和解析

生成：
    知识库.json

每讲完一章，把新的题库和新出现的报错加进来，重跑这个脚本就行。
**知识库是生成物，不要手改它 —— 改源材料。**

一条重要的设计决定
------------------
题库里的【答案】不进知识库，只进【解析】和【知识点】。

原因：这些题要拿去学习通做测验。如果助教能报答案，
学生把题一贴就知道选哪个，测验就废了。

所以助教的定位是：**把道理讲清楚，但不告诉你选哪个。**
真想知道答案，去做题、去问老师。
"""
import json
import os
import re

BASE = r'D:\2-jssw'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '知识库.json')


# ---------------------------------------------------------------- 报错

def jie_baocuo(path, lai_yuan, ping_tai):
    """从说明文件的【报错了怎么办】小节里，抽出「症状 -> 做法」。

    格式长这样（全角空格缩进）：

        　　ModuleNotFoundError: No module named 'yuyin'
        　　　　你没有打开整个文件夹，或者把文件挪走了。
        　　　　回到第 2 步重来。
    """
    if not os.path.exists(path):
        return []

    # 先把文件切成小节。两份说明的标题写法不同（一个用方括号，一个夹在 === 之间），
    # 但共同点是：标题都顶格、正文都缩进。所以按缩进切就够了。
    lines = open(path, encoding='utf-8').read().split(chr(10))
    secs, title, body = [], '(kai)', []
    for ln in lines:
        s = ln.replace('　', ' ')
        if not s.strip():
            body.append(ln)
            continue
        if set(s.strip()) <= set('=-'):          # 纯分隔线，不是标题
            continue
        if len(s) - len(s.lstrip(' ')) == 0:     # 顶格 = 新小节
            secs.append((title, body))
            title, body = ln.strip(), []
        else:
            body.append(ln)
    secs.append((title, body))

    out = []
    for t, b in secs:
        if '报错' not in t:
            continue
        cur = None
        for ln in b:
            s = ln.replace('　', ' ')
            if not s.strip():
                continue
            indent = len(s) - len(s.lstrip(' '))
            if indent <= 2:                      # 症状行（2 个全角空格）
                if cur:
                    out.append(cur)
                cur = {'症状': ln.strip(), '做法': [], '来源': lai_yuan,
                       '平台': ping_tai}
            elif cur:                            # 做法行（4 个及以上）
                cur['做法'].append(ln.strip())
        if cur:
            out.append(cur)

    # 只留下真正像报错的（有英文错误名，或明确的中文症状）
    keep = []
    for c in out:
        s = c['症状']
        if not c['做法']:
            continue
        if re.search(r'[A-Za-z]{4,}', s) or s.startswith('运行了') or s.startswith('"'):
            c['做法'] = ' '.join(c['做法'])
            keep.append(c)
    return keep


# ---------------------------------------------------------------- 安装步骤

def jie_buzhou(path, ping_tai):
    """抽出安装步骤的标题，让助教能回答"我卡在第几步"。"""
    if not os.path.exists(path):
        return []
    s = open(path, encoding='utf-8').read()
    out = []
    for m in re.finditer(r'第\s*(\d+)\s*步[　 ]+([^\n=]{4,40})', s):
        n, t = m.group(1), m.group(2).strip()
        if not any(x['序号'] == n for x in out):
            out.append({'序号': n, '标题': t, '平台': ping_tai})
    return out


# ---------------------------------------------------------------- 题库

def jie_tiku(path, zhang):
    """从题库 docx 里取【知识点】和【答案解析】。

    ★ 不取【答案】那一行 —— 见文件开头的说明。
    """
    if not os.path.exists(path):
        return []
    import docx
    d = docx.Document(path)
    txt = '\n'.join(p.text for p in d.paragraphs)
    blocks = [b.strip() for b in txt.split('\n\n') if b.strip()]

    out = []
    for b in blocks:
        m = re.match(r'^(\d+)\.【(.+?)】(.+)', b, re.S)
        if not m:
            continue
        xuhao, tixing, rest = m.group(1), m.group(2), m.group(3)
        head = rest.split('\n')[0].strip()

        jiexi = re.search(r'答案解析[：:]\s*(.+?)(?:\n知识点|$)', b, re.S)
        zhishi = re.search(r'知识点[：:]\s*(.+?)(?:\n|$)', b)
        nandu = re.search(r'难易程度[：:]\s*(.+?)(?:\n|$)', b)

        out.append({
            '章': zhang, '序号': int(xuhao), '题型': tixing,
            '题干': head,
            '解析': (jiexi.group(1).strip() if jiexi else ''),
            '知识点': [x.strip() for x in
                       (zhishi.group(1) if zhishi else '').split('；') if x.strip()],
            '难易': (nandu.group(1).strip() if nandu else ''),
        })
    return out


# ---------------------------------------------------------------- 主

def main():
    p_tong = os.path.join(BASE, r'发给学生\第1周-让电脑说话\使用说明.txt')
    p_mac = os.path.join(BASE, r'发给学生\第1周-让电脑说话\Mac版安装说明.txt')
    p_tiku = os.path.join(BASE, r'题库\计算思维-第1章-题库.docx')

    baocuo = jie_baocuo(p_tong, '使用说明.txt', '通用')
    baocuo += jie_baocuo(p_mac, 'Mac版安装说明.txt', 'Mac')

    # 去重：同一个症状两份文件都写了，留信息多的那份
    m = {}
    for c in baocuo:
        k = c['症状']
        if k not in m or len(c['做法']) > len(m[k]['做法']):
            m[k] = c
    baocuo = list(m.values())

    buzhou = jie_buzhou(p_tong, 'Windows') + jie_buzhou(p_mac, 'Mac')
    tiku = jie_tiku(p_tiku, 1)

    kb = {
        '版本': '2026-09-17',
        '覆盖章节': [1],
        '说明': '助教知识库。生成物，不要手改；改源材料后重跑 建知识库.py。'
                '题库部分只含知识点与解析，不含答案。',
        '报错': baocuo,
        '安装步骤': buzhou,
        '题库': tiku,
    }
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

    print('=' * 58)
    print('知识库已生成：%s' % OUT)
    print('=' * 58)
    print('  报错条目    %2d 条' % len(baocuo))
    for c in baocuo:
        print('      [%-4s] %s' % (c['平台'], c['症状'][:52]))
    print()
    print('  安装步骤    %2d 步' % len(buzhou))
    print('  题库        %2d 题（只取知识点与解析，不含答案）' % len(tiku))
    zhi = {}
    for t in tiku:
        for k in t['知识点']:
            zhi[k] = zhi.get(k, 0) + 1
    print('  涉及知识点  %2d 个，出现最多的：' % len(zhi))
    for k, v in sorted(zhi.items(), key=lambda kv: -kv[1])[:6]:
        print('      %-24s %d 题' % (k, v))
    print()
    print('  ⚠ 已确认：知识库里不含任何一道题的答案')
    leaked = [t for t in tiku if re.search(r'答案[：:]\s*[A-Z对错]', json.dumps(t, ensure_ascii=False))]
    print('     检查结果：%s' % ('发现 %d 处泄漏！' % len(leaked) if leaked else '干净'))


if __name__ == '__main__':
    main()
