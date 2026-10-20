"""Opt-in real-model tutor probe using only synthetic questions and excerpts.

Run via backend runtime stdin with --real-llm; no database or uploads read.
Responses are review samples, not a deterministic proof of teaching quality.
"""
import asyncio
import json
import sys
from types import SimpleNamespace


async def main():
    if '--real-llm' not in sys.argv:
        raise SystemExit('Pass --real-llm to send synthetic examples to the configured AI service')
    from llm_service import resolve_system_prompt, build_chat_messages, stream_chat
    system = '你当前是数学学习助手。\n' + resolve_system_prompt(
        SimpleNamespace(system_prompt='UNUSED_TEACHER_MARKER', tutor_enabled=True))
    quadratic = '[1]测试资料：因式分解可把一元二次方程化为两个一次因式的乘积等于零，再分别令因式为零。'
    problem = '如何解方程 x²-5x+6=0？'
    cases = [
        ('new_problem', [], problem, quadratic),
        ('stuck', [('user', problem), ('assistant', '可以先尝试因式分解。你准备怎样拆分这个二次式？')], '不会', quadratic),
        ('concept', [], '什么是平面的法向量？', '[1]测试资料：垂直于平面的非零向量叫做该平面的一个法向量。'),
        ('angle_citation', [], '已知空间向量 a=(1,2,-2)，b=(2,-1,2)，求两向量夹角的余弦值。',
         '[1]虚构测试讲义：两个非零向量 u、v 的夹角为 θ，满足 $\\cos\\theta=\\frac{\\vec u\\cdot\\vec v}{|\\vec u||\\vec v|}$。此公式适用于非零向量。'),
        ('numeric', [('user', problem), ('assistant', '需要两个负数的和为-5、乘积为6。你先尝试一个6的负因数？')],
         '-2', quadratic),
        ('completed', [('user', problem), ('assistant', '可以先因式分解，再分别令因式为零。')],
         '我算出 x=2 或 x=3，因为 (x-2)(x-3)=0，所以分别令两个因式为零。', quadratic),
    ]
    if '--case' in sys.argv:
        selected = sys.argv[sys.argv.index('--case')+1]
        cases = [case for case in cases if case[0] == selected]
        if not cases:
            raise SystemExit('Unknown synthetic case')
    async def probe(name, history, question, context):
        try:
            chunks = []
            async for chunk in stream_chat(build_chat_messages(system, history, question, context, True), timeout=45, temperature=0.2):
                chunks.append(chunk)
            return {'case': name, 'answer': ''.join(chunks)}
        except Exception as exc:
            return {'case': name, 'error': type(exc).__name__}
    results = await asyncio.wait_for(asyncio.gather(*(probe(*case) for case in cases)), timeout=60)
    print(json.dumps(results, ensure_ascii=False), flush=True)
    return int(any('error' in result or not result.get('answer') for result in results))


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
