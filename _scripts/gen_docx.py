import re
import sys
from enum import Enum
from pathlib import Path
from pprint import pprint

from bs4 import BeautifulSoup, Tag
from zipfile import ZipFile

"""
Requirements:
    - pip install bs4
"""

CONTENT_CLEAN_REGEX = (
    # (re.compile(r'‘’'), '\''),
    # (re.compile(r'“”'), '"'),
)
WORDS_CLEAN_REGEX = (
    # Remove floating punctuation
    (re.compile(r'(^|\s+)([ -/]|[:-@]|[\[-`]|[{-~])+(\s+|$)'), ' '),
    # Consecutive puntionation, which may cause issues, e.g. ". (quote followed by period) will
    # count the period as a word
    (re.compile(r'([ -/]|[:-@]|[\[-`]|[{-~]){2,}'), r'\1'),
)
WORDS_REGEX = re.compile(r'[-\w.\'’]+')
TOKEN_PROPERTY_REGEX = re.compile(r'//((?:[a-zA-Z0-9]+,)*)([-–\w]+)')


def to_bool(value):
    value = str(value).lower()
    
    if value == 'true' or value == '1':
        return True
    return False


class ParseMode(Enum):
    Properties = 1
    Content = 2
    Questions = 3
    End = 4


class DocParser:
    PROP_CONVERSIONS = dict(
        preview=to_bool,
    )
    PROP_REGEX = re.compile(r'(?:\s*(.+)\s*:)?\s*(.+)\s*')
    PROP_KEY_REGEX = re.compile(r'[\s_-]+')
    
    zip_file: ZipFile
    doc: BeautifulSoup
    body: Tag
    only_content = False
    
    def __init__(self):
        self.image_paths = dict()
        self.token_properties = dict()
        self.token_offset = 0
        pass
    
    def parse_rels(self, export_images: Path):
        rels_text = self.zip_file.read('word/_rels/document.xml.rels').decode('utf-8')
        rels = BeautifulSoup(rels_text, 'xml')
    
        is_first_image = True
        exported_images = []
        for rel in rels.Relationships.find_all('Relationship'):
            if not rel.has_attr('Type'):
                continue
            if rel['Type'] != 'http://schemas.openxmlformats.org/officeDocument/2006/' \
                              'relationships/image':
                continue
            if not rel.has_attr('Id') or not rel.has_attr('Target'):
                continue
        
            r_id, r_path = rel['Id'], rel['Target']
        
            if r_path[0] == '/':
                r_path = r_path.lstrip('/')
            else:
                r_path = f'word/{r_path}'
        
            self.image_paths[r_id] = r_path
        
            if export_images is not None:
                rel_file = Path(r_path)
                print(rel_file.suffix)
                if rel_file.suffix == '.jpeg':
                    rel_file = rel_file.with_suffix('.jpg')
                if is_first_image:
                    output_file = export_images.with_name(
                        f'{export_images.stem}{rel_file.suffix}')
                    is_first_image = False
                else:
                    output_file = export_images.with_name(
                        f'{export_images.stem}__{r_id}{rel_file.suffix}')
            
                i = 1
                while output_file.exists():
                    output_file = output_file.with_name(
                        f'{output_file.stem}_{i:02d}{output_file.suffix}')
            
                exported_images.append(output_file)
                with output_file.open('wb') as f:
                    f.write(self.zip_file.read(r_path))
                    pass
                pass
            pass
        
        return exported_images

    def parse_token_properties(self, m):
        token_index = m.start() + self.token_offset
        self.token_properties[token_index] = m.group(1).strip(',').split(',') \
            if m.group(1) else ['ignore']
    
        self.token_offset -= len(m.group(0)) - len(m.group(2))
        return m.group(2)
    
    @staticmethod
    def select_mode(heading):
        heading = heading.strip()
        if heading == 'Questions':
            return ParseMode.Questions
        return ParseMode.End
    
    def parse(self, path, export_images: Path = None):
        self.zip_file = ZipFile(path)
        # pprint(zip_file.namelist())

        if not self.only_content:
            exported_images = self.parse_rels(export_images)
        
            if export_images:
                return exported_images
    
        doc_text = self.zip_file.read('word/document.xml').decode('utf-8')
        self.doc = BeautifulSoup(doc_text, 'xml')
        self.body = self.doc.body
    
        if not self.body:
            return None
    
        mode = ParseMode.Properties
        questions = []
        props = dict(
            title=None,
            description=None,
            preview=False,
            image_align='',
            grade=None,
            score=None,
            difficulty=None,
            content=None,
            questions=questions,
            word_count=0,
        )
        content = []
        content_tags = []
        content_length = 0
        list_index = -1
        skip_questions = False
        question = None
    
        before_tags = []
        inner_tags = []
        after_tags = []
    
        for p in self.body.find_all('w:p'):
            properties_tag = p.find('pPr')
            if not properties_tag:
                properties_tag = self.doc.new_tag('p')
            style_tag = properties_tag.find('pStyle')
            style = style_tag['w:val'] if style_tag and style_tag.has_attr('w:val') else 'Normal'
        
            if mode == ParseMode.Properties:
                text = DocParser.get_text(p).strip()
            
                if not text:
                    continue
            
                if style == 'Heading1':
                    props['title'] = text
                elif style == 'Subtitle':
                    props['description'] = text
                elif style == 'ListParagraph':
                    key, value = DocParser.PROP_REGEX.match(text).groups()
                
                    if key is not None:
                        key = DocParser.PROP_KEY_REGEX.sub('_', key.lower())
                        if key in DocParser.PROP_CONVERSIONS:
                            value = DocParser.PROP_CONVERSIONS[key](value)
                        props[key] = value
                    else:
                        pass
                else:
                    mode = ParseMode.Content
                
                if mode == ParseMode.Properties:
                    continue

            if style == 'Heading2':
                mode = DocParser.select_mode(DocParser.get_text(p))
                continue
            
            if mode == ParseMode.Content:
                if style == 'ListParagraph':
                    list_id_tag = properties_tag.find('numId')
                    new_list_index = int(list_id_tag['w:val']) \
                        if list_id_tag and list_id_tag.has_attr('w:val') else -1
                
                    if new_list_index != list_index:
                        if list_index != -1:
                            before_tags.append(('/ul', ''))
                        list_index = new_list_index
                        if list_index != -1:
                            before_tags.append(('ul', ''))
                else:
                    if list_index != -1:
                        before_tags.append(('/ul', ''))
                        list_index = -1
                    pass
            
                if list_index != -1:
                    before_tags.append(('li', ''))
                    after_tags.append(('/li', ''))
                else:
                    before_tags.append(('p', ''))
                    after_tags.append(('/p', ''))
            
                text = []
                start_index = content_length
            
                for r in p.find_all('w:r'):
                    for child in r.contents:
                        if child.name == 't':
                            child_txt = str(child.string)
                            # Trim whitespace at the start of a paragraph
                            if not text:
                                child_txt = child_txt.lstrip()
                            if child_txt:
                                text.append(child_txt)
                                content_length += len(child_txt)
                        elif child.name == 'br':
                            # Trim trailing whitespace before other elements
                            if text:
                                text[-1] = text[-1].rstrip()
                            inner_tags.append((content_length, 'br'))
                            pass
            
                if text:
                    text = ''.join(text)
                    
                    # Trim trailing whitespace
                    t_length = len(text)
                    text = text.rstrip()
                    content_length -= t_length - len(text)
                    
                    if before_tags:
                        content_tags += [
                            (start_index, DocParser.tag(tag), DocParser.attribs(tag), dict())
                            for tag in before_tags]
                        before_tags.clear()
                    if inner_tags:
                        content_tags += [
                            (index, DocParser.tag(tag), DocParser.attribs(tag), dict())
                            for index, tag in inner_tags]
                        inner_tags.clear()
                    if after_tags:
                        content_tags += [
                            (content_length, DocParser.tag(tag), DocParser.attribs(tag), dict())
                            for tag in after_tags]
                        after_tags.clear()
                
                    content.append(f'{text}\n')
                    content_length += 1
                continue

            if mode == ParseMode.Questions:
                if skip_questions:
                    continue
                
                text = DocParser.get_text(p).strip()
                # Ignore template questions
                if text.startswith('QUESTION'):
                    skip_questions = True
                    continue
                
                if not question:
                    question = text
                else:
                    questions.append((question, text))
                    question = None
                continue
                
            if mode == ParseMode.End:
                break
    
        content = ''.join(content)
        if content_length > 0:
            content = content[:-1]
    
        if list_index != -1:
            content_tags.append((len(content), '/ul'))

        for regex, sub in CONTENT_CLEAN_REGEX:
            content = regex.sub(sub, content)
        self.token_properties.clear()
        self.token_offset = 0
        content = TOKEN_PROPERTY_REGEX.sub(self.parse_token_properties, content)

        words_text = props['description'] + '\n' + content
        props['word_count'] = self.word_count(words_text)
        
        props['content'] = content
        props['content_tags'] = content_tags

        self.zip_file.close()
        
        # pprint(props)
        return props, self.token_properties

    @staticmethod
    def tag(tag):
        return tag if isinstance(tag, str) else tag[0]

    @staticmethod
    def attribs(tag):
        return '' if isinstance(tag, str) else tag[1]
    
    @staticmethod
    def get_text(tag: Tag):
        output = []
        
        for r in tag.find_all('w:r'):
            for child in r.contents:
                if child.name == 't':
                    output.append(str(child.string))
                elif child.name == 'br':
                    output.append('\n')
        
        return ''.join(output)
    
    @staticmethod
    def word_count(text):
        for regex, sub in WORDS_CLEAN_REGEX:
            text = regex.sub(sub, text)
        split_words = WORDS_REGEX.findall(text)
        # pprint(split_words)
        return len(split_words)


if __name__ == '__main__':
    DocParser().parse(sys.argv[1])
