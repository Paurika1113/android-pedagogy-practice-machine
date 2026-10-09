#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate two standalone ESQ 1.0 question bank packages:
1. 山香 3600 题 · 教育学基础 (879 题单选，10 个章节独立为试卷，每卷细分为 15 题一组)
2. 燃领题本 · 教育学 (506 题单选，11 个章节独立为试卷，每卷细分为 15 题一组)
"""

import json
import os
import zipfile
from pathlib import Path

def build_esq_for_book(
    book_title,
    package_id,
    chapters,
    out_path,
    author="不背考点 · 教育学备考组",
    publisher="不背考点"
):
    print(f"\nBuilding ESQ for '{book_title}' ({package_id})...")
    manifest_papers = []
    paper_files = {}
    answer_files = {}
    
    total_q = 0
    
    for chap_idx, chap in enumerate(chapters):
        # year strictly numbered from 2001 upwards to maintain proper sort order in SQLite
        year = 2001 + chap_idx
        chap_title = chap['title']
        paper_key = f"{package_id}.c{chap_idx+1:02d}"
        
        # Filter single choice questions
        single_questions = [
            q for q in chap.get('questions', [])
            if q.get('qtype') == 'single' and len(q.get('options', [])) >= 2
        ]
        
        if not single_questions:
            continue
            
        unit_size = 15
        units = []
        answers_dict = {}
        
        chap_q_num = 1
        for unit_idx in range(0, len(single_questions), unit_size):
            chunk = single_questions[unit_idx:unit_idx + unit_size]
            u_num = (unit_idx // unit_size) + 1
            unit_key = f"{paper_key}.u{u_num:02d}"
            
            unit_questions = []
            for q in chunk:
                q_key = f"{paper_key}.q{chap_q_num:04d}"
                opts = []
                opt_letters = ['A', 'B', 'C', 'D', 'E', 'F']
                for opt_i, opt_text in enumerate(q.get('options', [])):
                    opts.append({
                        'key': opt_letters[opt_i],
                        'content': str(opt_text).strip()
                    })
                    
                correct_ans = str(q.get('answer', 'A')).strip().upper()
                if correct_ans not in opt_letters[:len(opts)]:
                    correct_ans = 'A'
                    
                meta = {
                    'explanation': q.get('explanation') or '',
                    'src': q.get('src') or '',
                    'section': q.get('section') or '',
                    'chapter': chap_title,
                    'book': book_title
                }
                
                unit_questions.append({
                    'questionKey': q_key,
                    'number': chap_q_num,
                    'type': 'single_choice',
                    'stem': q.get('stem', ''),
                    'score': 1,
                    'options': opts,
                    'metadata': meta
                })
                
                answers_dict[q_key] = {
                    'correctOption': correct_ans,
                    'score': 1
                }
                
                chap_q_num += 1
                total_q += 1
                
            unit_title = f"{chap_title} · 第{u_num}组 ({len(chunk)}题)"
            units.append({
                'unitKey': unit_key,
                'type': 'reading',
                'subtype': 'reading_a',
                'title': unit_title,
                'sequence': u_num,
                'passage': {
                    'blocks': [
                        {
                            'blockKey': 'p01',
                            'type': 'paragraph',
                            'text': f"【{book_title}】{chap_title}：第 {unit_idx + 1} - {unit_idx + len(chunk)} 题。单选题，每题 1 分。"
                        }
                    ]
                },
                'questions': unit_questions
            })
            
        paper_obj = {
            'paperKey': paper_key,
            'year': year,
            'title': chap_title,
            'subject': book_title,
            'units': units
        }
        
        answer_obj = {
            'paperKey': paper_key,
            'answers': answers_dict
        }
        
        paper_rel_path = f"papers/{year}.json"
        answer_rel_path = f"answers/{year}.json"
        
        paper_files[paper_rel_path] = json.dumps(paper_obj, ensure_ascii=False, indent=2)
        answer_files[answer_rel_path] = json.dumps(answer_obj, ensure_ascii=False, indent=2)
        
        manifest_papers.append({
            'paperKey': paper_key,
            'year': year,
            'path': paper_rel_path,
            'answerPath': answer_rel_path
        })
        
    manifest = {
        'format': 'esq',
        'schemaVersion': '1.0',
        'packageId': package_id,
        'contentVersion': '1.0.0',
        'title': book_title,
        'subject': book_title,
        'language': 'zh',
        'locale': 'zh-CN',
        'publisher': publisher,
        'license': {
            'spdx': 'CC0-1.0',
            'notice': '真题题库整理自公开回忆与教招备考资料。'
        },
        'source': {
            'type': 'past_papers',
            'description': f'{book_title} 单选题精选'
        },
        'papers': manifest_papers,
        'features': {
            'hasAnswers': True,
            'hasAiLabels': False,
            'hasAssets': False
        },
        'generator': {
            'name': 'Edu-App-Double-Book-Converter',
            'version': '1.0.0'
        }
    }
    
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
        for p_path, p_content in paper_files.items():
            z.writestr(p_path, p_content)
        for a_path, a_content in answer_files.items():
            z.writestr(a_path, a_content)
            
    print(f"Generated {out_path.name}: {len(manifest_papers)} chapters, {total_q} questions, size: {out_path.stat().st_size / 1024:.1f} KB")

def main():
    root = Path(__file__).resolve().parent.parent.parent
    public_dir = root / 'android-english-multiple-choice-practice-machine' / 'frontend' / 'public'
    
    # 1. 山香 3600 题 · 教育学基础
    shanxiang_file = root / 'app' / 'seed' / 'quiz-3600.json'
    with open(shanxiang_file, 'r', encoding='utf-8') as f:
        sx_data = json.load(f)
    sx_chapters = [c for c in sx_data['decks'][0]['chapters'] if c.get('part') == '教育学基础']
    
    build_esq_for_book(
        book_title='山香3600题·教育学',
        package_id='cn.edu.shanxiang.pedagogy.3600',
        chapters=sx_chapters,
        out_path=public_dir / 'internal-question-bank.esq'
    )
    
    # 2. 燃领题本 · 教育学
    ranling_file = root / 'app' / 'seed' / 'ranling-quiz.json'
    with open(ranling_file, 'r', encoding='utf-8') as f:
        rl_data = json.load(f)
    rl_chapters = [c for c in rl_data['decks'][0]['chapters'] if c.get('part') == '教育学']
    
    build_esq_for_book(
        book_title='燃领题本·教育学',
        package_id='cn.edu.ranling.pedagogy.quiz',
        chapters=rl_chapters,
        out_path=public_dir / 'internal-question-bank-ranling.esq'
    )

if __name__ == '__main__':
    main()
