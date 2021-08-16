"""
Requirements:
    - pip install clipboard
    - pip install PyHyphen
    - pip install textatistic
"""
import os
import re
import sys
from pathlib import Path
from pprint import pprint

import clipboard
from textatistic import Textatistic

from gen_docx import DocParser

DOC_NAME_CLEAN_REGEX = re.compile(r'^\d+-\d+-\w+-\d+-')


class DifficultyChecker:
    def __init__(self):
        self.doc_parser = DocParser()
        self.doc_parser.only_content = True
        self.document_name = ''
        self.difficulty = '-'
        self.text = ''

        print(',,,'.join((
            'Document',
            'Difficulty',
            'ARI',
            'ARI Grade',
            'ARI Age',
            'Flesch',
            'Flesch Difficulty',
            'Flesch Kincaid',
            'Flesch Kincaid Grade',
            'Flesch Kincaid Difficulty',
            'Dale-Chall',
            'Dale-Chall Grade',
            'Dale-Chall Difficulty',
            'Coleman-Liau',
            'Coleman-Liau Grade',
            'Coleman-Liau Difficulty',
            'SMOG',
            'SMOG Grade',
            'SMOG Difficulty',
            'Gunning Fog',
            'Gunning Fog Grade',
            'Gunning Fog Difficulty',
            'Bormuth',
            'Char Count',
            'Word Count',
            'Syllable Count',
            'Sentence Count',
        )))
        
        if len(sys.argv) == 1:
            self.run(clipboard.paste())
            pass
        else:
            in_args = sys.argv[1:]
            for p in in_args:
                self.run(Path(p))
            pass
        pass
    
    def run(self, text_or_path):
        if isinstance(text_or_path, Path):
            self.document_name = DOC_NAME_CLEAN_REGEX.sub('', text_or_path.stem)
        
            if text_or_path.suffix == '.docx':
                props = self.doc_parser.parse(text_or_path)
                description = props['description'].rstrip('.')
                content = props['content']
                self.text = f'{description}\n{content}'
                self.difficulty = props['difficulty']
            else:
                with text_or_path.open('r', encoding='utf-8') as f:
                    self.text = f.read()
        else:
            self.document_name = 'Clipboard'
            self.text = text_or_path

        # readability.summarize(self.text)

        s = Textatistic(self.text)
        data = s.dict()
        data['dale_chall_count'] = data['word_count'] - data['notdalechall_count']
        data['awl'] = data['char_count'] / data['word_count']
        data['asl'] = data['word_count'] / data['sent_count']
        data['asc'] = data['sent_count'] / data['word_count']
        data['afw'] = data['dale_chall_count'] / data['word_count']
        self.calc_ari_score(data)
        self.calc_coleman_liau_score(data)
        self.calc_bormuth_score(data)
        # pprint(data)

        data = (
            self.document_name,
            self.difficulty,
            *self.ari_grade(data),
            *self.flesch_grade(data),
            *self.fleschkincaid_grade(data),
            *self.dalechall_grade(data),
            *self.coleman_liau_grade(data),
            *self.smog_grade(data),
            *self.gunningfog_grade(data),
            data['bormuth_score'],
            data['char_count'],
            data['word_count'],
            data['sybl_count'],
            data['sent_count'],
        )
        print(',,,'.join(map(str, data)))
        
        pass

    @staticmethod
    def ari_grade(data):
        score = int(data['ari_score'])
        grade = ''
        age = ''
        if score <= 1:
            grade = 'Kindergarten'
            age = '5-6'
        elif score == 2:
            grade = '1st, 2nd'
            age = '6-7'
        elif score == 3:
            grade = '3rd'
            age = '7-9'
        elif 4 <= score <= 12:
            grade = f'{score}th'
            age = f'{5 + score}-{6 + score}'
        elif score == 13:
            grade = 'College'
            age = '18-24'
        elif score >= 14:
            grade = 'Professor'
            age = '24+'
        return data['ari_score'], grade, age

    @staticmethod
    def flesch_grade(data):
        score = data['flesch_score']
        
        if score >= 90:
            diff = 'Very Easy'
        elif score >= 80:
            diff = 'Easy'
        elif score >= 70:
            diff = 'Fairly Easy'
        elif score >= 60:
            diff = 'Medium'
        elif score >= 50:
            diff = 'Difficult'
        elif score >= 30:
            diff = 'Very Difficult'
        else:
            diff = 'Confusing'
        
        return score, diff

    @staticmethod
    def fleschkincaid_grade(data):
        score = data['fleschkincaid_score']
        
        if score >= 18:
            grade = 'Professional'
            diff = 'Extremely Difficult'
        elif score >= 16:
            grade = 'College Graduate'
            diff = 'Very Difficult'
        elif score >= 13:
            grade = 'College'
            diff = 'Difficult'
        elif score >= 10:
            grade = '10th, 11th, 12th'
            diff = 'Fairly Difficult'
        elif score >= 8:
            grade = '8th, 9th'
            diff = 'Medium'
        elif score >= 7:
            grade = '7th'
            diff = 'Fairly Easy'
        elif score >= 6:
            grade = '6th'
            diff = 'Easy'
        else:
            grade = '5th'
            diff = 'Very Easy'
        
        return score, grade, diff

    @staticmethod
    def dalechall_grade(data):
        score = data['dalechall_score']
        
        if score >= 10:
            grade = 'College Graduate'
            diff = 'Very Difficult'
        elif score >= 9:
            grade = 'College'
            diff = 'Difficult'
        elif score >= 8:
            grade = '11th, 12th'
            diff = 'Fairly Difficult'
        elif score >= 7:
            grade = '9th, 10th'
            diff = 'Medium'
        elif score >= 6:
            grade = '7th, 8th'
            diff = 'Medium Low'
        elif score >= 5:
            grade = '5th, 6th'
            diff = 'Easy'
        else:
            grade = '4th'
            diff = 'Very Easy'
        
        return score, grade, diff

    @staticmethod
    def coleman_liau_grade(data):
        score = data['coleman_liau_score']
        
        if score >= 17:
            grade = 'Professional'
            diff = 'Very Difficult'
        elif score >= 13:
            grade = 'College'
            diff = 'Difficult'
        elif score >= 11:
            grade = '11th, 12th'
            diff = 'Fairly Difficult'
        elif score >= 8:
            grade = '8th, 9th, 10th'
            diff = 'Medium'
        elif score >= 7:
            grade = '7th'
            diff = 'Fairly Easy'
        elif score >= 6:
            grade = '6th'
            diff = 'Easy'
        else:
            grade = '5th'
            diff = 'Very Easy'
        
        return score, grade, diff

    @staticmethod
    def smog_grade(data):
        score = data['smog_score']
        
        if score >= 211:
            grade = 'Professional'
            diff = 'Extremely Difficult'
        elif score >= 183:
            grade = 'College Graduate'
            diff = 'Very Difficult'
        elif score >= 91:
            grade = 'College'
            diff = 'Difficult'
        elif score >= 73:
            grade = '12th'
            diff = 'Fairly Difficult'
        elif score >= 57:
            grade = '11th'
            diff = 'Fairly Difficult'
        elif score >= 43:
            grade = '10th'
            diff = 'Fairly Difficult'
        elif score >= 21:
            grade = '8th, 9th'
            diff = 'Medium'
        elif score >= 13:
            grade = '7th'
            diff = 'Fairly Easy'
        elif score >= 7:
            grade = '6th'
            diff = 'Easy'
        elif score >= 3:
            grade = '6th'
            diff = 'Very Easy'
        else:
            grade = '4th'
            diff = 'Very Easy'
        
        return score, grade, diff

    @staticmethod
    def gunningfog_grade(data):
        score = data['gunningfog_score']
        
        if score >= 18:
            grade = 'Professional'
            diff = 'Extremely Difficult'
        elif score >= 17:
            grade = 'College Graduate'
            diff = 'Very Difficult'
        elif score >= 13:
            grade = 'College'
            diff = 'Difficult'
        elif score >= 9:
            grade = '9th-12th'
            diff = 'Fairly Difficult'
        elif score >= 8:
            grade = '8th'
            diff = 'Medium'
        elif score >= 7:
            grade = '7th'
            diff = 'Fairly Easy'
        elif score >= 6:
            grade = '6th'
            diff = 'Easy'
        else:
            grade = '5th'
            diff = 'Very Easy'
        
        return score, grade, diff
    
    @staticmethod
    def calc_ari_score(data):
        data['ari_score'] = 4.71 * data['awl'] + 0.5 * data['asl'] - 21.43
        pass
    
    @staticmethod
    def calc_coleman_liau_score(data):
        data['coleman_liau_score'] = 0.0588 * (data['awl'] * 100) -\
            0.296 * (data['asc'] * 100) - 15.8
        pass
    
    @staticmethod
    def calc_bormuth_score(data):
        data['bormuth_score'] = 0.886593 -\
            (data['awl'] * 0.03640) +\
            (data['afw'] * 0.161911) -\
            (data['asl'] * 0.21401) -\
            (data['asl'] * 0.000577) -\
            (data['asl'] * 0.000005)
        # data['bormuth_score'] = 0.886593 -\
        #     0.03640 * data['awl'] +\
        #     0.161911 * data['afw'] -\
        #     0.21401 * data['asl'] -\
        #     0.000577 * (data['asl'] ** 2) -\
        #     0.000005 * (data['asl'] ** 3)
        pass
    
    pass


if __name__ == '__main__':
    DifficultyChecker()
    if 'PYCHARM_HOSTED' not in os.environ:
        print('Press any key to exit.')
        input()
