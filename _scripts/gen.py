"""
Usage:
- A new .docx file: Will generate a new html file, using the data and file name of the .dat file
  automatically prepending a new index and the date.
  Will rename the .docx file to match
- A .docx file with a corresponding html file: Will regenerate that html file
- A folder: Will generate/regenerate all .docx or html files

Requirements:
- pip install titlecase (https://pypi.org/project/titlecase/)
- pip install Pillow (https://pypi.org/project/Pillow/)
- pip install spacy (See full installation instructions: https://spacy.io/usage)
"""
import json
import os
import pickle
import re
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from pprint import pprint
from typing import List, Optional

from PIL import Image
from titlecase import titlecase

from difficulty_checker import DifficultyChecker
from gen_docx import DocParser

DO_NLP = True
CACHE_TOKENS = False
if DO_NLP:
    import spacy

UPDATE_JSON_INDEX_ONLY = False

TOKEN_CACHE_FILE = Path(r'data/__token_cache.pickle')

SLUG_REGEXES = (
    (re.compile(r'\s*\(\d+\)$'), ''),
    (re.compile(r'\W+'), '-'),
)
PROP_REGEX = re.compile(r'^\[(.+)\]$')
CONTENT_INDENT_REGEX = re.compile(r'^(\s*).*__CONTENT__', re.MULTILINE)
BASE_NAME_REGEX = re.compile(r'\d+-\d+-[a-z]+-\d+-', re.MULTILINE)
FILENAME_DATE_REGEX = re.compile(r'\d+-(\d+-[a-zA-Z]+-\d+).+')
SLUG_TO_TITLE_REGEX = re.compile(r'-+')
IGNORE_LIST_SPLIT_REGEX = re.compile(r'\s+')
TERM_SPLIT_REGEX = re.compile(r'[-–\s]+')
HYPEN_REGEX = re.compile(r'^[-–]+$')
ARTICLE_INDEX_LIST_END_REGEX = re.compile(r'([ \t]*)(<!-- __LIST_END__ -->)')
QUESTIONS_REGEX = re.compile(r'(\t*)__\[QUESTIONS__(.+)__QUESTIONS]__\n*', re.DOTALL)
QUESTION_REGEX = re.compile(r'(\t+)__\[QUESTION__(.+)__QUESTION]__', re.DOTALL)
DIFFICULT_WORDS_REGEX = re.compile(r'(\t*)__\[DIFFICULT_WORDS__(.+)__DIFFICULT_WORDS]__\n*', re.DOTALL)
DIFFICULT_WORD_ITEM_REGEX = re.compile(r'(\t+)__\[ITEM__(.+)__ITEM]__', re.DOTALL)

PARSE_ATTRIBS_REGEX = re.compile(r'\s*(.+?)\s*="([^"]*?)"')
CLASS_LIST_SPLIT_REGEX = re.compile(r'\s+')

DATA_BASE = Path('../data')
ARTICLES_DATA_BASE = DATA_BASE / 'articles'
TPL_HTML_FILE = Path('../_template.html')
INDEX_FILE = Path('data/index')
ARTICLE_INDEX_FILE = Path('../articles.html')
JSON_INDEX_FILE = ARTICLES_DATA_BASE / 'articles_index.json'

TITLE_ABBREVIATIONS = {'sa', 'uk'}

VOCAB_SIZE = 'sm'


class ArticleGenerator:
    output_child: Optional[List]
    output_paragraph: Optional[List]
    output_parent: Optional[List]
    
    def __init__(self):
        self.content_indent = ''
        
        self.json_output = []
        self.text_buffer = []
        self.output_paragraph = None
        self.output_parent = None
        self.output_child = None
        pass

    @staticmethod
    def get_file_args(last_file):
        if len(sys.argv) == 1:
            return [Path(last_file)] if last_file else []
    
        files = []
    
        for arg in sys.argv[1:]:
            arg_path = Path(arg)
            is_file = arg_path.is_file()
        
            if not is_file and not arg_path.is_dir():
                print(f'Argument "{str(arg_path)}" is not a valid file or folder')
                continue
        
            if is_file and ():
                continue
        
            arg_files = arg_path.iterdir() if not is_file else (arg_path,)
        
            for file in arg_files:
                if not file.exists():
                    continue
                if file.suffix != '.docx' or file.name.startswith('_'):
                    continue
                files.append(file)
                pass
    
        return files

    def titlecase(self, text):
        return titlecase(text, callback=self.titlecase_abbreviations)

    @staticmethod
    def titlecase_abbreviations(word, **kwargs):
        if word.lower() in TITLE_ABBREVIATIONS:
            return word.upper()

    @staticmethod
    def add_to_json_index(base_name, props):
        if not JSON_INDEX_FILE.exists():
            data = dict(articles=[])
        else:
            with JSON_INDEX_FILE.open('r', encoding='utf-8') as f:
                data = json.load(f)

        new_data = dict(
            slug=base_name,
            title=props['title'],
            difficulty=props['difficulty'],
            wordCount=props['word_count'],
            date=props['date']
        )

        found_match = False
        for i in range(len(data['articles'])):
            article_data = data['articles'][i]
            if isinstance(article_data, list) and article_data[0] == base_name or \
                    isinstance(article_data, dict) and article_data['slug'] == base_name:
                data['articles'][i] = new_data
                found_match = True
                break
        
        if not found_match:
            data['articles'].insert(0, new_data)
        
        with JSON_INDEX_FILE.open('w', encoding='utf-8') as f:
            json.dump(data, f, indent='\t')
        pass

    def add_to_index(self, output_name, base_name, props):
        # ArticleGenerator.add_to_json_index(base_name, props)
        
        if not ARTICLE_INDEX_FILE.exists():
            print(f'Article index file not found "{ARTICLE_INDEX_FILE.name}"')
            return

        with ARTICLE_INDEX_FILE.open('r', encoding='utf-8') as f:
            text = f.read()

        m = ARTICLE_INDEX_LIST_END_REGEX.search(text)
        if not m:
            print('Cannot find list end in article index')
            return

        indent = m.group(1)
        base_name = SLUG_TO_TITLE_REGEX.sub(' ', base_name)
        new_item = f'{indent}<li><a href="{output_name}.html">{self.titlecase(base_name)}</a></li>'
        start, end = m.start(), m.end()
        text = text[:start] + f'{new_item}\n{indent}{m.group(2)}' + text[end:]

        with ARTICLE_INDEX_FILE.open('w', encoding='utf-8') as f:
            f.write(text)
        pass
    
    def add_tags(self, content_text, content_tags):
        inline_tags = {'br', '/li', '/p', 'span', '/span', '/b', '/strong', 'strong'}
        block_tags = {'ul', '/ul', 'ol', '/ol'}
        indent = ''
        output = []
        end_index = len(content_text)
        for index, tag_name, attribs, data in reversed(content_tags):
            if end_index != index:
                output.append(content_text[index:end_index])
        
            if tag_name in block_tags and tag_name[0] != '/':
                indent = indent[:-1]
        
            pre_whitespace = ''
            if index != 0 and tag_name not in inline_tags:
                if tag_name in block_tags and tag_name[0] == '/':
                    pre_whitespace += '\n'
                pre_whitespace += f'{self.content_indent}{indent}'
        
            if tag_name in block_tags:
                post_whitespace = '\n'
            else:
                post_whitespace = ''
        
            if tag_name == 'br':
                post_whitespace = f'\n{self.content_indent}{indent}\t'
        
            if attribs:
                attribs = f' {attribs.lstrip()}'
            
            output.append(f'{pre_whitespace}<{tag_name}{attribs}>{post_whitespace}')
            end_index = index
        
            if tag_name in block_tags and tag_name[0] == '/':
                indent += '\t'
            pass
        
        return ''.join(reversed(output))

    def run(self):
        if not INDEX_FILE.exists():
            print(f'Cannot find index file: "{str(INDEX_FILE)}"')
            return
        if not TPL_HTML_FILE.exists():
            print(f'Cannot find template html file: "{str(TPL_HTML_FILE)}"')
            return
        
        with TPL_HTML_FILE.open('r', encoding='utf-8') as f:
            tpl_data = f.read()
            # Find content indentation
            m = CONTENT_INDENT_REGEX.search(tpl_data)
            self.content_indent = m.group(1) if m else ''
    
        with INDEX_FILE.open('r', encoding='utf-8') as f:
            try:
                value = f.read().strip().split('\n')
                start_index, last_file = int(value[0]), value[1].strip() if len(value) > 1 else ''
                start_last_file = last_file
            except ValueError:
                value = re.sub(r'\s+', ' ', value[0])
                print(f'Unable to parse index from index file: "{value}"')
                return
            index = start_index
        
        questions_tpl = ListTemplate()
        tpl_data = questions_tpl.fetch(tpl_data, 'QUESTIONS', 'QUESTION')
        if tpl_data is None:
            print('Could not find questions section template')
            return
        
        diff_words_tpl = ListTemplate()
        tpl_data = diff_words_tpl.fetch(tpl_data, 'DIFFICULT_WORDS', 'ITEM')
        if tpl_data is None:
            print('Could not find difficult words section template')
            return
        
        files = ArticleGenerator.get_file_args(last_file)
        if not files:
            print(f'No .md or .html files found in input')
            return
        
        longest_term = 1
        word_list = dict()
        # for list_type in ('ielts', 'cet4', 'cet6'):
        for list_type in ('ielts', 'cet6', 'extra'):
            freqs = ('low', 'med', 'high') if list_type != 'extra' else ('', )
            for freq in freqs:
                freq_str = f'-{freq}' if freq else ''
                with Path(f'data/words-{list_type}{freq_str}.txt').open('r', encoding='utf-8') as f:
                    for word in f.read().splitlines():
                        word = word.strip()
                        word_count = len(TERM_SPLIT_REGEX.split(word))
                        if word_count > longest_term:
                            longest_term = word_count
                        
                        if word not in word_list:
                            word_data = []
                            word_list[word] = word_data
                        else:
                            word_data = word_list[word]
    
                        word_data.append((list_type, freq))
                        
        doc_parse = DocParser()
        checker = DifficultyChecker()
        
        if DO_NLP:
            nlp = spacy.load(f'en_core_web_{VOCAB_SIZE}')
        else:
            nlp = None
        
        for file in files:
            print(f'-- Generating {file.stem} --')
            html_file = Path(f'../{file.stem}.html')
            data_file = Path(f'data-articles/{file.stem}.docx')
            last_file = str(data_file)
            is_new = not html_file.exists()
            
            if is_new:
                current_data = datetime.today().strftime('%d-%B-%Y').lower()
                slugged_name = file.stem.strip().lower()
                for regex, sub in SLUG_REGEXES:
                    slugged_name = regex.sub(sub, slugged_name).strip('-')
                output_name = f'{index:02d}-{current_data}-{slugged_name}'
                index += 1
            else:
                output_name = file.stem
            
            base_name = BASE_NAME_REGEX.sub('', output_name)
    
            image_path = Path(f'../img/{base_name}.jpg')
            if not image_path.exists():
                output_images = Path(f'../src/{base_name}.jpg')
                exported_images = doc_parse.parse(data_file, output_images)
                if not exported_images:
                    print(f'Could not find image "{image_path}" and no images to export from doc')
                else:
                    extract_list = '", "'.join((f'{img.parent.name}/{img.name}'
                                                for img in exported_images))
                    print(f'Images extracted for: "{extract_list}"')

                if is_new:
                    index -= 1
                    
                continue
            try:
                with Image.open(image_path) as img:
                    img_width, img_height = img.size
            except Exception:
                print(f'Unable to open image: "{str(image_path)}"')
                img_width, img_height = 1200, 1200
                
            # Read data
            props, token_properties = doc_parse.parse(data_file)
            content_tags = props['content_tags']
            questions = props['questions']
            difficult_words = props['difficult_words']
            del props['content_tags']
            del props['questions']
            del props['difficult_words']
            
            # Validate properties
            for name in ['title', 'description', 'content']:
                if props[name] is None:
                    print(f'"{name}" property not found')
                    props[name] = ''
    
            content_text = props['content']

            props['is_new'] = is_new
            props['date'] = FILENAME_DATE_REGEX.match(output_name).group(1)
            props['title'] = self.titlecase(props['title'].lower())
            props['description'] = props['description'].rstrip('.')
    
            props['image'] = base_name
            props['preview'] = props['image'] if not props['preview'] else f'{base_name}-preview'
            props['image_class'] = []
            if props['image_align']:
                props['image_class'].append('align-' + props['image_align'])
            del props['image_align']
            props['image_class'] = ' '.join(props['image_class'])
            if props['image_class']:
                props['image_class'] = ' ' + props['image_class']
            
            # Calculate rating
            if not props['difficulty'] or not props['grade']:
                full_text = props['description'] + '\n' + content_text
                checker.run(full_text)
                
                if not props['grade']:
                    props['grade'] = checker.grade
                    props['score'] = checker.score
                    if not props['difficulty']:
                        props['difficulty'] = checker.difficulty
                else:
                    props['score'], _ = checker.calculate_score(props['grade'])
                    if not props['difficulty']:
                        props['difficulty'] = checker.calculate_difficulty(props['score'])
            
            grade = props['grade']
            score = props['score']
            props['score'] = f'{score:.2f}'
            props['grade'] = f'{grade:.2f}'
            props['score_nice'] = int(score)
            props['grade_class'] = props['difficulty'].lower().replace(' ', '-')

            if UPDATE_JSON_INDEX_ONLY:
                ArticleGenerator.add_to_json_index(base_name, props)
                continue

            if DO_NLP or CACHE_TOKENS:
                # Highlight IELTS words
                combined_tags = []
                content_tags_index = 0
                
                ignore_words = IGNORE_LIST_SPLIT_REGEX.split(props['ignore'])\
                    if 'ignore' in props else []
                ignore_words = set([word.lower() for word in ignore_words])
    
                doc = None
                
                if CACHE_TOKENS:
                    if TOKEN_CACHE_FILE.exists():
                        with TOKEN_CACHE_FILE.open('rb') as f:
                            doc = pickle.load(f)
                
                if doc is None:
                    if not DO_NLP:
                        raise Exception('NLP document cache not found. Please set DO_NLP to True,'
                                        ' run again to generate the cache, then DO_NLP can be set'
                                        ' to false.')
                    
                    doc = nlp(content_text)
    
                    with TOKEN_CACHE_FILE.open('wb') as f:
                        pickle.dump(doc, f)
    
                tokens = list(doc)
                num_tokens = len(tokens)
                i = 0
                while i < num_tokens:
                    token = tokens[i]
                    i += 1
                    word_text: str = token.orth_
                    # upos = token.pos_
                    lemma = str(token.lemma_).lower()
                    token_index = token.idx
                    token_props = token_properties[token_index]\
                        if token_index in token_properties else []
                    # print(f'{len(token)} "{token}"', token_props)
                    
                    # Find multi-word terms in the dictionary
                    has_whitespace = bool(token.whitespace_)
                    terms = [(i - 1, has_whitespace, token)]
                    j = i
                    while j < num_tokens and len(terms) < longest_term:
                        term_token = tokens[j]
                        if term_token.whitespace_:
                            has_whitespace = True
                        if has_whitespace or not HYPEN_REGEX.match(term_token.orth_):
                            terms.append((j, has_whitespace, term_token))
                        j += 1
        
                    for j in range(len(terms), 1, -1):
                        sub_terms = terms[:j]
                        has_whitespace = any([bool(has_whitespace)
                                              for _, has_whitespace, term_token in sub_terms[:-1]])
                        sub_terms_strs = [term_token.orth_.lower()
                                          for _, _, term_token in sub_terms]
        
                        for delimiter in (' ', '-'):
                            require_whitespace = delimiter == ' '
                            # Don't allow whitespace beteen hyphens
                            if require_whitespace != has_whitespace:
                                continue
        
                            term_str = delimiter.join(sub_terms_strs)
        
                            if term_str in word_list:
                                word_text = term_str
                                lemma = term_str
                                end_index = sub_terms[-1][0]
                                i = end_index + 1
                                j = False
                                break
                        
                        if not j:
                            break
                        pass
        
                    # print(i - 1, word_text, f'{{{lemma}}}', f'"{token.whitespace_}"')
        
                    word_freq = None
                    data_lemma = None
                    
                    if word_text.lower() not in ignore_words and 'ignore' not in token_props:
                        if word_text in word_list:
                            word_freq = word_list[word_text]
                        elif lemma in word_list:
                            word_freq = word_list[lemma]
                            data_lemma = lemma
                    
                    if word_freq:
                        data = dict(
                            word_lists=set(
                                [list_type for list_type, freq in word_freq] +
                                [f'{list_type}-{freq}' for list_type, freq in word_freq])
                        )
                        
                        if data_lemma is not None:
                            lemma_attr = f' data-lemma="{data_lemma}"'
                            data['lemma'] = data_lemma
                        else:
                            lemma_attr = ''
                        
                        word_lists = ' '.join(list_type for list_type, freq in word_freq)
                        freq_list = [f'{list_type}-{freq}' for list_type, freq in word_freq if freq]
                        freqs = (' ' + ' '.join(freq_list)).rstrip()
                        
                        tag_name = 'span'
                        attribs = f'class="word {word_lists}{freqs}"{lemma_attr} tabindex="-1"'
                        
                        while content_tags_index < len(content_tags):
                            tag_data = content_tags[content_tags_index]
                            tag_index = tag_data[0]
                            if tag_index > token_index:
                                break
                            combined_tags.append(tag_data)
                            content_tags_index += 1
                            pass

                        combined_tags.append((token_index, tag_name, attribs, data))
                        combined_tags.append((token_index + len(word_text), f'/{tag_name}', '', dict()))
                    
                    pass
        
                if content_tags_index < len(content_tags):
                    combined_tags += content_tags[content_tags_index:]
                    pass
    
                content_tags = combined_tags

            # pprint(content_tags)
            content_raw = content_text
            content_text = self.add_tags(content_text, content_tags)
            
            props['content'] = content_text
    
            props['img_width'] = str(img_width)
            props['img_height'] = str(img_height)
            
            # These properties should not substituted in the template
            for key in ('ignore', ):
                if key in props:
                    del props[key]
            
            output_html = tpl_data
            
            # Question substitutions
            questions_text = questions_tpl.replace_items(('QUESTION', 'ANSWER'), questions)
            output_html = questions_tpl.insert(output_html, questions_text)

            # Difficult word substitutions
            diff_words_text = diff_words_tpl.replace_items(('WORD', 'DEF'), difficult_words)
            output_html = diff_words_tpl.insert(output_html, diff_words_text)
            
            # Do substitutions
            for key, value in props.items():
                key = f'__{key.upper()}__'
                output_html = output_html.replace(key, str(value))
                
            # Output
            with Path(f'../{output_name}.html').open('w', encoding='utf-8') as f:
                f.write(output_html)
            
            self.wechat_export(base_name, props, content_raw, content_tags)

            if is_new:
                rename_file = file.with_name(f'{output_name}.docx')
                file.rename(rename_file)
                last_file = str(rename_file)
                self.add_to_index(output_name, base_name, props)
    
        # Update index
        if index != start_index or last_file != start_last_file:
            with INDEX_FILE.open('w', encoding='utf-8') as f:
                f.write('\n'.join([str(index), last_file]))
        pass
    
    def wechat_export(self, base_name, props, content_text, content_tags):
        self.parse_json(content_text, content_tags)
        data = dict(
            title=props['title'],
            description=props['description'],
            wordCount=props['word_count'],
            difficulty=props['difficulty'],
            grade=float(props['grade']),
            rating=float(props['score']),
            content=self.json_output,
        )
        
        if not props['is_new']:
            date = datetime.strptime(props['date'], '%d-%B-%Y').replace(hour=12)
            data['date'] = date.isoformat()
        
        import_data_file = Path('data/wechat_import/data.json')
        if import_data_file.exists():
            with import_data_file.open('r') as f:
                import_data = json.load(f)
        else:
            import_data = dict()

        import_data[base_name] = data

        with import_data_file.open('w') as f:
            json.dump(import_data, f, indent='\t')
        
        pass
    
    def json_reset(self):
        self.text_buffer.clear()
        self.json_output = []
        self.text_buffer = []
        self.output_paragraph = None
        self.output_parent = None
        self.output_child = None
    
    def push_text(self, text):
        self.text_buffer.append(text)
        pass
    
    def push_data(self, data):
        self.flush_text()

        self.ensure_para()
        self.output_parent.append(data)
        pass
    
    def new_paragraph(self):
        self.flush_text()
        self.pop_child()
        self.output_paragraph = None
        self.output_parent = None
        pass
    
    def flush_text(self):
        if not self.text_buffer:
            return

        self.ensure_para()
        self.output_parent.append([''.join(self.text_buffer)])
        self.text_buffer.clear()
        pass
    
    def ensure_para(self):
        if self.output_parent is None:
            self.output_paragraph = []
            self.output_parent = self.output_paragraph
            self.json_output.append(self.output_parent)
    
    def push_child(self):
        self.ensure_para()
        self.output_child = []
        self.output_parent.append(self.output_child)
        self.output_parent = self.output_child
    
    def pop_child(self):
        if self.output_child is None:
            return

        self.output_parent = self.output_paragraph
        self.output_child = None
    
    def parse_json(self, content_text, content_tags):
        end_index = 0
        self.json_reset()
        i = 0
        while i < len(content_tags):
            index, tag_name, _, data = content_tags[i]
            i += 1
        
            # if tag_name[0] == '/':
            #     continue
        
            # print(index, tag_name, data)
        
            if end_index != index:
                self.push_text(content_text[end_index:index])
                end_index = index
        
            if tag_name == 'p':
                self.new_paragraph()
                end_index = index
                continue
        
            if tag_name == 'br':
                self.push_text('\n')
            if tag_name == 'ul':
                self.new_paragraph()
            if tag_name == '/ul':
                # self.pop_child()
                self.new_paragraph()
            if tag_name == 'li':
                # self.pop_child()
                # self.new_paragraph()
                self.push_data((chr(2),))
                # self.push_child()
                pass
            elif tag_name == 'span':
                self.flush_text()
            
                # Get the closing /span tag
                index, _, _, _ = content_tags[i]
                i += 1
                run = [content_text[end_index:index]]
                if 'word_lists' in data and data['word_lists']:
                    run.append(' '.join(data['word_lists']))
                if 'lemma' in data:
                    run.append(data['lemma'])
                self.push_data(run)
                end_index = index
                continue
    
        self.flush_text()
    
    def get_json(self, props, content_text, content_tags):
        self.parse_json(content_text, content_tags)
        
        data = dict(
            title=props['title'],
            description=props['description'],
            wordCount=props['word_count'],
            difficulty=props['difficulty'],
            grade=float(props['grade']),
            rating=float(props['score']),
            content=self.json_output,
            date=props['date'],
        )
        return data
    
    @staticmethod
    def parse_attribs(attribs):
        data = dict()
        for name, value in PARSE_ATTRIBS_REGEX.findall(attribs):
            data[name] = value
        
        return data


class ListTemplate:
    container_marker: str
    indent: str
    tpl: str
    item_indent: str
    item_tpl: str
    
    def fetch(self, tpl_data, container_marker, item_marker):
        self.container_marker = container_marker
        container_regex = re.compile(r'(\t*)__\[M__(.+)__M]__\n*'.replace('M', container_marker), re.DOTALL)
        item_regex = re.compile(r'(\t+)__\[M__(.+)__M]__'.replace('M', item_marker), re.DOTALL)

        m = container_regex.search(tpl_data)
        if not m:
            return None
        
        tpl_start = tpl_data[:m.start()]
        tpl_end = tpl_data[m.end():]
        self.indent = m.group(1)
        self.tpl = self.indent + m.group(2)
        im = item_regex.search(self.tpl)
        if not im:
            print('Invalid item template')
            return None

        item_tpl_start = self.tpl[:im.start()]
        item_tpl_end = self.tpl[im.end():]
        self.item_indent = im.group(1)
        self.item_tpl = im.group(2)

        self.tpl = f'{item_tpl_start}__CONTENT__{item_tpl_end}\n'
        
        return f'{tpl_start}__LIST_{container_marker}__{tpl_end}'

    def replace_items(self, keys, data):
        items = []
        
        for item in data:
            text = self.item_tpl
            
            for key, value in zip(keys, item):
                text = text.replace(f'__{key}__', value)
            
            items.append(text)
        
        if items:
            text = self.replace_content('\n'.join(items))
        else:
            text = ''
        
        return text
    
    def replace_content(self, content):
        return self.tpl.replace(f'__CONTENT__', content)
    
    def insert(self, data, content):
        return data.replace(f'__LIST_{self.container_marker}__', content)
    
    pass


if __name__ == "__main__":
    try:
        ArticleGenerator().run()
    except Exception as e:
        traceback.print_exc()
    
    if 'PYCHARM_HOSTED' not in os.environ:
        print('Press any key to exit.')
        input()
