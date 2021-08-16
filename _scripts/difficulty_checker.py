"""
Requirements:
    - pip install clipboard
    - pip install textatistic
"""
import math
import os
import re
import statistics
import sys
import traceback
from pathlib import Path

import clipboard
from textatistic import Textatistic

from gen_docx import DocParser

DOC_NAME_CLEAN_REGEX = re.compile(r'^\d+-\d+-\w+-\d+-')
# DIFFICULTIES = ('Easy', 'Medium', 'Difficult', 'Very Difficult')
SCORE_ADJUSTMENTS = dict(
    ari_score=0.8,
    coleman_liau_score=0.9,
    gunningfog_score=0.9,
)
DIFFICULTIES = ('Extremely Easy', 'Very Easy', 'Easy', 'Medium', 'Difficult', 'Very Difficult')

DEBUG_OUTPUT = False


class DifficultyChecker:
    # The real grade 0-14 and in some cases higher
    grade: float
    # Normalised grade from 0-14 to 0-10, and rounded to the nearest 0.5
    score: float
    # Score rounded to the nearest 0.5
    score_nice: float
    # Maps score to a difficulty word
    difficulty: str
    
    ari_score: float
    fleschkincaid_score: float
    coleman_liau_score: float
    gunningfog_score: float
    
    def __init__(self):
        pass
    
    def run(self, text):
        s = Textatistic(text)
        data = s.dict()
        data['dale_chall_count'] = data['word_count'] - data['notdalechall_count']
        data['awl'] = data['char_count'] / data['word_count']
        data['asl'] = data['word_count'] / data['sent_count']
        data['asc'] = data['sent_count'] / data['word_count']
        data['afw'] = data['dale_chall_count'] / data['word_count']
        self.calc_ari_score(data)
        self.calc_coleman_liau_score(data)
        
        # for name, multiplier in SCORE_ADJUSTMENTS.items():
        #     data[name] *= multiplier
        
        self.ari_score = data['ari_score']
        self.fleschkincaid_score = data['fleschkincaid_score']
        self.coleman_liau_score = data['coleman_liau_score']
        self.gunningfog_score = data['gunningfog_score']
        
        scores = ('ari_score', 'fleschkincaid_score', 'coleman_liau_score', 'gunningfog_score')
        self.grade = statistics.mean(data[name] for name in scores)
        self.score = min(max((self.grade / 13.0) * 10, 0), 10)
        self.score_nice = round(self.score * 2) / 2
        
        index = round(self.score / 10 * (len(DIFFICULTIES) - 1))
        self.difficulty = DIFFICULTIES[index]
        
        pass
    
    @staticmethod
    def calc_ari_score(data):
        data['ari_score'] = 4.71 * data['awl'] + 0.5 * data['asl'] - 21.43
        pass
    
    @staticmethod
    def calc_coleman_liau_score(data):
        data['coleman_liau_score'] = 0.0588 * (data['awl'] * 100) - \
                                     0.296 * (data['asc'] * 100) - 15.8
        pass
    
    @staticmethod
    def ease_in_sine(x):
        return 1 - math.cos((x * math.pi) / 2)
        pass
    
    @staticmethod
    def ease_in_quad(x):
        return x * x
        pass
    
    @staticmethod
    def ease_in_cubic(x):
        return x * x * x
        pass
    
    pass


def run():
    f = None
    orig_stdout = None
    
    if DEBUG_OUTPUT:
        orig_stdout = sys.stdout
        f = open('out.txt', 'w')
        sys.stdout = f
    
    checker = DifficultyChecker()
    doc_parser = DocParser()
    doc_parser.only_content = True
    
    files = []
    if len(sys.argv) == 1:
        text = clipboard.paste()
        files.append(('Clipboard', text, doc_parser.word_count(text)))
        pass
    else:
        in_args = sys.argv[1:]
        for p in in_args:
            path = Path(p)
            document_name = DOC_NAME_CLEAN_REGEX.sub('', path.stem)
            
            if path.suffix == '.docx':
                props, token_properties = doc_parser.parse(path)
                description = props['description'].rstrip('.')
                content = props['content']
                text = f'{description}\n{content}'
                word_count = props['word_count']
            else:
                with path.open('r', encoding='utf-8') as f:
                    text = f.read()
                    word_count = doc_parser.word_count(text)
            
            files.append((document_name, text, word_count))
        pass
    
    for document_name, text, word_count in files:
        checker.run(text)
        if not DEBUG_OUTPUT:
            print(f'{document_name}:\n    "{checker.difficulty}"'
                  f'  Score: {checker.score_nice:02.1f}/10  Grade: {checker.grade:02.2f}'
                  f'  Words: {word_count}')
        else:
            values = (document_name,
                      checker.grade,
                      checker.score,
                      checker.difficulty,
                      checker.ari_score,
                      checker.fleschkincaid_score, checker.coleman_liau_score,
                      checker.gunningfog_score)
            print('\t'.join(map(str, values)))
        pass
    
    if DEBUG_OUTPUT:
        sys.stdout = orig_stdout
        f.close()
    pass


if __name__ == '__main__':
    try:
        run()
    except Exception as e:
        print(traceback.format_exc())
        pass
    
    if 'PYCHARM_HOSTED' not in os.environ:
        print('Press any key to exit.')
        input()
