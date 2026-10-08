#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert 教育学基础客观真题 (from app/seed/quiz-3600.json) into ESQ 1.0 package.
"""

import json
import os
import zipfile
from pathlib import Path

def main():
    root_dir = Path(__file__).resolve().parent
    seed_path = root_dir / 'app' / 'seed' / 'quiz-3600.json'
    out_esq_path = root_dir / 'android-english-multiple-choice-practice-machine' / 'frontend' / 'public' / 'internal-question-bank.esq'
    
    print(f"Reading {seed_path}...")
    with open(seed_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    deck = data['decks'][0]
    # Filter chapters belonging to 教育学基础
    chapters = [c for c in deck['chapters'] if c.get('part') == '教育学基础']
    print(f"Found {len(chapters)} chapters in 教育学基础.")
    
    # We will build papers for each chapter
    # Base year starts at 2017 to 2026 (10 chapters)
    papers = []
    manifest_papers = []
    paper_files = {} # relative_path -> json_str
    answer_files = {}
    
    total_questions = 0
    global_q_index = 0
    
    for chap_idx, chap in enumerate(chapters):
        year = 2017 + chap_idx
        chap_title = chap['title']
        paper_key = f"cn.edu.jiaozong.pedagogy.{year}"
        
        # Filter single choice questions
        single_questions = [q for q in chap['questions'] if q.get('qtype') == 'single' and len(q.get('options', [])) >= 2]
        
        # Split into units of 15 questions
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
                global_q_index += 1
                q_key = f"{paper_key}.q{chap_q_num:04d}"
                
                # options format
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
                    'chapter': chap_title
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
                total_questions += 1
                
            unit_title = f"{chap_title} · 第{u_num}组"
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
                            'text': f"本组为【{chap_title}】精选客观真题练习（第 {unit_idx + 1} - {unit_idx + len(chunk)} 题）。每题 1 分，点击选项作答。"
                        }
                    ]
                },
                'questions': unit_questions
            })
            
        paper_obj = {
            'paperKey': paper_key,
            'year': year,
            'title': f"{chap_title} 专项特训卷",
            'subject': "教育学基础",
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
        'packageId': 'cn.edu.jiaozong.pedagogy.core',
        'contentVersion': '1.0.0',
        'title': '福建教综·教育学基础真题特训题库',
        'subject': '教育学基础',
        'language': 'zh',
        'locale': 'zh-CN',
        'publisher': '不背考点 · 教育学备考组',
        'license': {
            'spdx': 'CC0-1.0',
            'notice': '福建教招真题整理自考生回忆与公开考试解析。'
        },
        'source': {
            'type': 'past_papers',
            'description': '山香教育学基础 3600 题单选题精选'
        },
        'papers': manifest_papers,
        'features': {
            'hasAnswers': True,
            'hasAiLabels': False,
            'hasAssets': False
        },
        'generator': {
            'name': 'Edu-App-Pedagogy-Converter',
            'version': '1.0.0'
        }
    }
    
    # Write to ZIP
    print(f"Total papers: {len(manifest_papers)}, total single-choice questions: {total_questions}")
    print(f"Packing into {out_esq_path}...")
    out_esq_path.parent.mkdir(parents=True, exist_ok=True)
    
    with zipfile.ZipFile(out_esq_path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
        for p_path, p_content in paper_files.items():
            z.writestr(p_path, p_content)
        for a_path, a_content in answer_files.items():
            z.writestr(a_path, a_content)
            
    size_kb = out_esq_path.stat().st_size / 1024
    print(f"Successfully generated {out_esq_path.name} ({size_kb:.1f} KB)")

if __name__ == '__main__':
    main()
