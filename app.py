# -*- coding: utf-8 -*-
"""助教小莉 · 《计算思维》课程答疑

    本地跑：  streamlit run app.py
    线上：    Streamlit Community Cloud

设计上的一条原则
----------------
**判断由规则给出，不由大模型给出。**

报错匹配走确定性的字符串比对（匹配.py）—— 匹配不上就说匹配不上，
绝不编一个听起来很专业的答案。

这和课上讲的是同一件事：能用确定规则解决的，不要交给大模型。
大模型很熟悉 ModuleNotFoundError，熟到会自信地给你一个和本课程无关的解法。
"""
import os

import streamlit as st

from 匹配 import 载入, 找报错, 判断把握, 找知识点, 所有知识点

st.set_page_config(page_title='助教小莉 · 计算思维答疑',
                   page_icon='🙋', layout='centered')

st.markdown("""
<style>
  .block-container{max-width:860px;padding-top:2rem}
  .zdy{background:#EFF6FF;border-left:4px solid #2563EB;
       padding:14px 18px;border-radius:6px;margin:10px 0}
  .ok {background:#ECFDF5;border-left:4px solid #059669;
       padding:14px 18px;border-radius:6px;margin:10px 0}
  .no {background:#FEF2F2;border-left:4px solid #DC2626;
       padding:14px 18px;border-radius:6px;margin:10px 0}
  .gr {color:#6B7280;font-size:0.88rem}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def kb():
    return 载入()


K = kb()

st.title('🙋 助教小莉')
st.markdown('<span class="gr">上外贤达《计算思维》· 课程答疑　｜　'
            '知识库 %s　覆盖第 %s 章</span>'
            % (K['版本'], '、'.join(str(x) for x in K['覆盖章节'])),
            unsafe_allow_html=True)

with st.sidebar:
    st.header('我能答什么')
    st.markdown("""
**能答**

- 装不上、跑不起来、报红字
- 装到第几步了、下一步做什么
- 课上讲过的概念

**不能答**

- 作业该怎么做
- 测验题选哪个 —— **我不会告诉你答案**
- 课程内容之外的事

答不上来的，我会直说，然后请你去问老师。
**我宁可说"我不知道"，也不给你编一个。**
""")
    st.divider()
    st.caption('报错 %d 条 ｜ 安装步骤 %d 步 ｜ 概念 %d 个'
               % (len(K['报错']), len(K['安装步骤']), len(所有知识点(K))))

t1, t2, t3 = st.tabs(['🚑 报错急救', '📦 装环境', '📘 概念速查'])

# ================================================================ 报错
with t1:
    st.markdown('**把红色的报错整段复制过来**，越完整越好。'
                '也可以贴 `诊断.py` 的输出。')
    ping = st.radio('你的电脑', ['不确定', 'Windows', 'Mac'],
                    horizontal=True, index=0)
    txt = st.text_area('报错内容', height=170, label_visibility='collapsed',
                       placeholder='例如：\nModuleNotFoundError: '
                                   "No module named 'yuyin'")

    if st.button('查一下', type='primary', use_container_width=True):
        if not txt.strip():
            st.warning('先把报错贴进来')
        else:
            r = 找报错(K, txt, None if ping == '不确定' else ping)
            把握, 说 = 判断把握(r)

            if 把握 == 'none':
                st.markdown("""<div class="no">
<b>这个我没见过。</b><br><br>
我的知识库里现在只有第 1 章的常见报错，这一条不在里面。<br>
<b>请把下面三样发给小莉或老师：</b><br>
　① 你的代码截图　② 完整的报错截图（红色那一大段，要完整）　③ 你做到第几步了<br><br>
说清楚卡在第几步，比说"我不行了"快得多。
</div>""", unsafe_allow_html=True)
                st.caption('答不上来就直说 —— 这是我被设计成的样子，'
                           '不会给你编一个听起来很专业的答案。')
            else:
                条目, 分, 命中 = r[0]
                box = 'ok' if 把握 == 'sure' else 'zdy'
                st.markdown(
                    '<div class="%s"><b>%s：%s</b><br><br>%s</div>'
                    % (box, 说, 条目['症状'], 条目['做法']),
                    unsafe_allow_html=True)
                st.caption('命中：%s　｜　适用：%s　｜　出处：%s'
                           % ('、'.join(命中[:5]), 条目['平台'], 条目['来源']))

                if len(r) > 1:
                    with st.expander('还可能是这几条（%d）' % (len(r) - 1)):
                        for 条, f, h in r[1:4]:
                            st.markdown('**%s**' % 条['症状'])
                            st.write(条['做法'])
                            st.divider()

    st.divider()
    with st.expander('我知道的报错，一共 %d 条' % len(K['报错'])):
        for c in K['报错']:
            st.markdown('**[%s]** `%s`' % (c['平台'], c['症状']))
            st.caption(c['做法'])

# ================================================================ 装环境
with t2:
    p = st.radio('选一个', ['Windows', 'Mac'], horizontal=True)
    bu = [b for b in K['安装步骤'] if b['平台'] == p]
    if not bu:
        st.info('这个平台的步骤还没录进来')
    else:
        for b in bu:
            st.markdown('**第 %s 步　%s**' % (b['序号'], b['标题']))
    if p == 'Mac':
        st.markdown("""<div class="no">
<b>Mac 同学最容易漏的一步</b><br><br>
装完 Python 之后，一定要双击 <code>Install Certificates.command</code>。<br>
漏了它，程序能跑，但一联网合成语音就报
<code>CERTIFICATE_VERIFY_FAILED</code>。<br>
Windows 没有这一步，Mac 才有 —— 这是这一周问得最多的问题。
</div>""", unsafe_allow_html=True)
    st.caption('完整步骤见发给你们的【使用说明.txt】和【Mac版安装说明.txt】，'
               '学习通第 1 讲还有配套视频。')

# ================================================================ 概念
with t3:
    st.markdown('课上讲过的概念，在这儿查。'
                '**注意：我只讲道理，不报测验答案。**')
    dian = 所有知识点(K)
    c1, c2 = st.columns([2, 3])
    with c1:
        pick = st.selectbox('挑一个知识点',
                            ['（自己输）'] + ['%s（%d）' % (k, n) for k, n in dian])
    with c2:
        word = st.text_input('或者输入关键词', placeholder='比如：抽象、import、算法')

    q = word.strip() if word.strip() else (
        pick.split('（')[0] if pick != '（自己输）' else '')

    if q:
        hits = 找知识点(K, q)
        if not hits:
            st.info('没查到「%s」。换个说法试试，或者去问老师。' % q)
        else:
            st.caption('找到 %d 条相关讲解' % len(hits))
            for t, f in hits[:6]:
                with st.container(border=True):
                    st.markdown('**%s**' % t['题干'])
                    st.write(t['解析'])
                    st.caption('第 %d 章 · 第 %d 题 · %s · 知识点：%s'
                               % (t['章'], t['序号'], t['难易'],
                                  '、'.join(t['知识点'])))
            if len(hits) > 6:
                st.caption('还有 %d 条没显示。换个更具体的词能找得更准。'
                           % (len(hits) - 6))

st.divider()
st.markdown('<span class="gr">'
            '这个助教的知识全部来自课程材料，不是大模型自己想的。'
            '匹配不上就会说匹配不上。<br>'
            '知识库随课程进度更新，每讲完一章加一章。'
            '</span>', unsafe_allow_html=True)
