# -*- coding: utf-8 -*-
"""报错匹配 —— 助教的确定性内核

    from 匹配 import 载入, 找报错
    kb = 载入()
    结果 = 找报错(kb, 学生粘贴的红字)

为什么这一层不用大模型
----------------------
那十几条报错，特征串都极其独特：CERTIFICATE_VERIFY_FAILED、U+3000、
ModuleNotFoundError……学生把红字一贴，字符串一对就中了。

用规则匹配的好处是**它不会编**：匹配不上就说匹配不上，不会给你造一个
听起来很专业的错误答案。大模型在这种场景下反而危险 ——
它对 ModuleNotFoundError 太熟了，熟到会自信地告诉你一个和我们课程无关的解法。

这正是课上讲的那条：**能用确定规则解决的，不要交给大模型。**

大模型只在这一层匹配不中的时候兜底，而且只许看检索到的条目。
"""
import json
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
KB_PATH = os.path.join(BASE, '知识库.json')


def 载入(path=KB_PATH):
    with open(path, encoding='utf-8') as f:
        kb = json.load(f)
    for c in kb['报错']:
        c['特征'] = _提特征(c['症状'])
    return kb


# ---------------------------------------------------------------- 特征

# 这些词单独出现没有区分度，必须配合别的特征
弱词 = {'error', 'no', 'not', 'name', 'module', 'found', 'command',
        'install', 'the', 'is', 'of', 'in'}


def _提特征(症状):
    """从一条症状里提取用来比对的特征。

    分两类：
        强特征 —— 独一无二，命中就基本确定（CERTIFICATE_VERIFY_FAILED、U+3000）
        标识符 —— 用来区分同类报错（yuyin 和 edge_tts 都是 ModuleNotFoundError）
    """
    s = 症状
    强, 标识符, 中文 = [], [], []

    # 英文错误类名：XxxError / XxxException
    for m in re.findall(r'\b([A-Z][A-Za-z]*(?:Error|Exception))\b', s):
        强.append(m)

    # 全大写的特殊标记，如 CERTIFICATE_VERIFY_FAILED
    for m in re.findall(r'\b([A-Z][A-Z_]{6,})\b', s):
        强.append(m)

    # U+3000 这类码位
    for m in re.findall(r'U\+[0-9A-Fa-f]{4}', s):
        强.append(m.upper())

    # 引号里的标识符：'yuyin'、'edge_tts'、'speak'
    for m in re.findall(r"'([A-Za-z_][A-Za-z0-9_]*)'", s):
        标识符.append(m)

    # 小写的固定短语：command not found: pip / permission denied
    low = s.lower()
    for phrase in ('command not found', 'permission denied',
                   'invalid non-printable character', 'invalid character',
                   'unexpected indent'):
        if phrase in low:
            强.append(phrase)
    # command not found 后面跟的是哪个命令，要区分 pip 和 python
    m = re.search(r'command not found:\s*([a-z0-9]+)', low)
    if m:
        标识符.append(m.group(1))

    # 纯中文症状：切成两字片段来比。
    # 不能整句比 —— "运行了但是没声音" 和学生写的
    # "我点了运行，但是一点声音都没有" 一个字都对不上，但意思是同一件事。
    # 切成 运行/但是/声音 这样的片段，重叠几个就算命中。
    if not 强:
        for run in re.findall(r'[一-鿿]{2,}', s):
            中文 += [run[i:i + 2] for i in range(len(run) - 1)]
        中文 = list(dict.fromkeys(中文))

    return {'强': [x for x in 强 if x.lower() not in 弱词],
            '标识符': 标识符, '中文': 中文}


# ---------------------------------------------------------------- 匹配

def 找报错(kb, 文本, 平台=None):
    """在知识库里找匹配的报错。

    返回 [(条目, 得分, 命中了什么), ...]，按得分从高到低。
    得分 >= 3 基本可以确定；1–2 是"可能是这个"；没有就是没有。
    """
    if not 文本 or not 文本.strip():
        return []
    t = 文本
    low = t.lower()

    结果 = []
    for c in kb['报错']:
        f = c['特征']
        分 = 0
        命中 = []

        for x in f['强']:
            if x.lower() in low:
                # 越长越独特：CERTIFICATE_VERIFY_FAILED 这种命中就该一锤定音
                分 += 5 if len(x) >= 12 else 3
                命中.append(x)

        for x in f['标识符']:
            # 标识符要求边界，避免 'python' 命中 'python3'
            if re.search(r'\b%s\b' % re.escape(x), t, re.I):
                分 += 2
                命中.append(x)

        if not f['强'] and f['中文']:          # 纯中文症状，看两字片段重叠了多少
            hit = [w for w in f['中文'] if w in t]
            bi = len(hit) / len(f['中文'])
            if len(hit) >= 2 and bi >= 0.2:
                分 += 2 + len(hit)
                命中 += hit[:5]

        if 平台 and c['平台'] not in ('通用', 平台):
            分 -= 1                           # 平台不符，降权但不排除
        elif 平台 and c['平台'] == 平台:
            分 += 1                           # 平台专属的条目，优先于通用条目

        if 分 > 0:
            结果.append((c, 分, 命中))

    结果.sort(key=lambda x: -x[1])

    # 同一类错误里，标识符没命中的要让位。
    # 例：贴的是 No module named 'edge_tts'，就不该把 'yuyin' 那条排前面。
    if len(结果) >= 2 and 结果[0][1] == 结果[1][1]:
        有标识 = [r for r in 结果 if any(
            i in r[2] for i in r[0]['特征']['标识符'])]
        if 有标识:
            结果 = 有标识 + [r for r in 结果 if r not in 有标识]

    return 结果


def 判断把握(结果):
    """把得分翻译成人话。"""
    if not 结果:
        return 'none', '没找到对得上的'
    分 = 结果[0][1]
    if 分 >= 5:
        return 'sure', '就是这个'
    if 分 >= 3:
        return 'likely', '很可能是这个'
    return 'maybe', '可能是这个，不太确定'


# ---------------------------------------------------------------- 概念

def 找知识点(kb, 词):
    """按知识点或题干关键词查题库，返回讲解素材。

    ★ 只返回【解析】，不返回【答案】—— 见 建知识库.py 开头的说明。
    """
    if not 词 or not 词.strip():
        return []
    词 = 词.strip()
    out = []
    for t in kb['题库']:
        分 = 0
        if any(词 in k for k in t['知识点']):
            分 += 3
        if 词 in t['题干']:
            分 += 2
        if 词 in t['解析']:
            分 += 1
        if 分:
            out.append((t, 分))
    out.sort(key=lambda x: -x[1])
    return out


def 所有知识点(kb):
    m = {}
    for t in kb['题库']:
        for k in t['知识点']:
            m[k] = m.get(k, 0) + 1
    return sorted(m.items(), key=lambda kv: (-kv[1], kv[0]))


# ---------------------------------------------------------------- 自检

if __name__ == '__main__':
    kb = 载入()
    print('知识库：报错 %d 条，题库 %d 题' % (len(kb['报错']), len(kb['题库'])))
    print()

    样例 = [
        ('ModuleNotFoundError: No module named \'yuyin\'', 'yuyin 那条'),
        ('ModuleNotFoundError: No module named \'edge_tts\'', 'edge_tts 那条'),
        ('ssl.SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED] '
         'certificate verify failed', '证书那条'),
        ('  File "a.py", line 2\n    print("B")\nIndentationError: unexpected indent',
         '前导空格那条'),
        ('SyntaxError: invalid non-printable character U+3000', '全角空格那条'),
        ('NameError: name \'speak\' is not defined', 'speak 没 import'),
        ('zsh: command not found: pip', 'pip 那条'),
        ('我点了运行，但是一点声音都没有', '没声音那条'),
        ('我的电脑蓝屏了', '应该匹配不上'),
    ]
    对 = 0
    for 文本, 期望 in 样例:
        r = 找报错(kb, 文本)
        把握, 说 = 判断把握(r)
        if r:
            条目, 分, 命中 = r[0]
            print('  %-10s %-5s %s' % (说, '%d分' % 分, 条目['症状'][:46]))
            print('             命中：%s' % '、'.join(命中[:4]))
            print('             期望：%s' % 期望)
        else:
            print('  %-10s ——    （期望：%s）' % (说, 期望))
        print()
