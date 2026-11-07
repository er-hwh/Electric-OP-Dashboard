"""
Sync script to create elearning_quizzes table and populate with 78 questions from static/data/gr_sr_quizzes.json
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath('.'))

from app import create_app
from database import db
from models import ELearningQuiz

def sync_quizzes():
    app = create_app()
    with app.app_context():
        # Create table if not exists
        db.create_all()
        
        json_path = os.path.join(app.root_path, 'static', 'data', 'gr_sr_quizzes.json')
        if not os.path.exists(json_path):
            print(f"Error: {json_path} does not exist.")
            return

        with open(json_path, 'r', encoding='utf-8') as f:
            quizzes = json.load(f)

        print(f"Loaded {len(quizzes)} quiz items from JSON.")

        # Clear existing entries in elearning_quizzes
        ELearningQuiz.query.delete()

        # Insert all items
        for q in quizzes:
            record = ELearningQuiz(
                quiz_id_str=q.get('id'),
                chapter_no=q.get('chapter_no'),
                chapter_title=q.get('chapter_title'),
                rule_ref=q.get('rule_ref'),
                question=q.get('question'),
                options_json=json.dumps(q.get('options', []), ensure_ascii=False),
                correct_index=q.get('correct_index', 0),
                explanation=q.get('explanation', ''),
                difficulty=q.get('difficulty', 'Intermediate')
            )
            db.session.add(record)

        db.session.commit()
        count = ELearningQuiz.query.count()
        print(f"Successfully synced {count} quiz questions into MySQL 'elearning_quizzes' table!")

if __name__ == '__main__':
    sync_quizzes()
