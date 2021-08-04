"""
Requirements:
    - pip install clipboard
    - pip install colorama
"""
import os
import re
import sys
from enum import Enum
from pathlib import Path
from pprint import pprint
from typing import List, Dict

import clipboard
from colorama import init, Fore, Back, Style

from gen_docx import DocParser

WORDS_REGEX = re.compile(r'[-\w.\'’_]+')
WORD_CLEAN_REGEX = re.compile(r'[^-\w_\'’]+')
DOC_NAME_CLEAN_REGEX = re.compile(r'^\d+-\d+-\w+-\d+-')
LEVEL_CLR = dict(
    A1=Fore.RED,
    A2=Fore.GREEN,
    B1=Fore.YELLOW,
    B2=Fore.BLUE,
    C1=Fore.MAGENTA,
    C2=Fore.CYAN,
)
LEVEL_CLR['?'] = Fore.WHITE

INDENT = '    '
BAR_WIDTH = 120


class Mode(Enum):
    CERF = 1,
    FREQUENCY = 2,


class Checker:
    words: List[str]
    
    def __init__(self, mode):
        self.mode = mode
        
        init(autoreset=True)
        self.cerf_words = dict()
        self.word_frequencies = dict()
        self.doc_parser = DocParser()
        self.doc_parser.only_content = True
        self.document_name = ''
        self.difficulty = '-'
        self.text = ''
        self.total_words = 0
        
        if self.mode == Mode.CERF:
            self.load_cerf_words()
        elif self.mode == Mode.FREQUENCY:
            print('\t'.join((
                'Document',
                'Difficulty',
                'Word Count',
                'Longest Word',
                'Average Word Length',
                'Word Frequency Sum',
                'Average Word Frequency',
                'Unknown Words'
            )))
            self.load_frequency_words()

        if len(sys.argv) == 1:
            self.run(clipboard.paste())
            pass
        else:
            in_args = sys.argv[1:]
            for p in in_args:
                self.run(Path(p))
            pass
        pass
    
    def load_cerf_words(self):
        with open('data/cefr-raw.tsv', 'r', encoding='utf-8') as f:
            for line in f.read().splitlines()[1:]:
                word, guide_word, level, pos, topic = line.split('\t')
                if ' ' in word:
                    continue
                self.cerf_words[word.lower()] = level
        pass
    
    def load_frequency_words(self):
        with open('data/english-word-frequency.txt', 'r', encoding='utf-8') as f:
            for line in f.read().splitlines():
                word, freq = line.split('\t')
                self.word_frequencies[word] = int(freq)
        pass
    
    def run(self, text):
        if isinstance(text, Path):
            self.document_name = DOC_NAME_CLEAN_REGEX.sub('', text.stem)
        
            if text.suffix == '.docx':
                props = self.doc_parser.parse(text)
                description = props['description'].rstrip('.')
                content = props['content']
                self.text = f'{description}\n{content}'
                self.difficulty = props['difficulty']
            else:
                with text.open('r', encoding='utf-8') as f:
                    self.text = f.read()
        else:
            self.document_name = 'Clipboard'
    
        words = WORDS_REGEX.findall(self.text)
        final_words = []
        for word in words:
            word = WORD_CLEAN_REGEX.sub('', word).lower().strip()
            if not word:
                continue
            final_words.append(word)
            
        self.words = final_words
        self.total_words = len(self.words)
        
        if self.mode == Mode.CERF:
            self.calculate_cerf()
        elif self.mode == Mode.FREQUENCY:
            self.calculate_frequency()
    
    def calculate_cerf(self):
        levels = dict()
        for word in self.words:
            level = self.cerf_words[word] if word in self.cerf_words else '?'
            if level in levels:
                levels[level] += 1
            else:
                levels[level] = 1
        
        levels = [(level, count) for level, count in levels.items()]
        levels = sorted(levels, key=lambda item: item[0] if item[0] != '?' else 'ZZZ')
        print(f'-- {self.document_name} ({self.difficulty}) --')
        bar = []
        for level, count in levels:
            bar.append(LEVEL_CLR[level] + '█' * round(count / self.total_words * BAR_WIDTH))
        print(f'{INDENT}{"".join(bar)}')
        print(INDENT +
              '  '.join(f'{LEVEL_CLR[level]}{level}:{count}/{(count / self.total_words * 100):.1f}%'
                        for level, count in levels))
        pass
    
    def calculate_frequency(self):
        longest_word = 0
        word_length_sum = 0
        word_frequency_count = 0
        word_frequency_sum = 0
        for word in self.words:
            longest_word = max(longest_word, len(word))
            word_length_sum += len(word)
            if word in self.word_frequencies:
                word_frequency_sum += self.word_frequencies[word]
                word_frequency_count += 1
            pass

        average_word_length = word_length_sum / self.total_words
        average_word_frequency = word_frequency_sum / word_frequency_count
        data = (
            self.document_name,
            self.difficulty,
            self.total_words,
            longest_word,
            average_word_length,
            word_frequency_sum,
            average_word_frequency,
            len(self.words) - word_frequency_count
        )
        print('\t'.join(f'{v:.1f}' if isinstance(v, float) else str(v) for v in data))
        pass
    
    pass


if __name__ == '__main__':
    Checker(Mode.FREQUENCY)
    if 'PYCHARM_HOSTED' not in os.environ:
        print('Press any key to exit.')
        input()
