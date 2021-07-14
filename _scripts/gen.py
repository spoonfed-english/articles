"""
Usage:
- A new .dat file: Will generate a new html file, using the data and file name of the .dat file
  automatically prepending a new index and the date.
  Will rename the .dat file to match
- A .dat file with a corresponding html file: Will regenerate that html file
- A folder: Will generate/regenerate all .dat or html files

Requirements:
- pip install titlecase (https://pypi.org/project/titlecase/)
- pip install Pillow (https://pypi.org/project/Pillow/)
- pip install nltk
    - nltk.download('wordnet')
"""
import os
import re
import sys
import traceback
from datetime import datetime
from pathlib import Path
from pprint import pprint

from PIL import Image
from titlecase import titlecase
import spacy

from gen_docx import parse_doc

SLUG_REGEX = re.compile(r'\W+')
PROP_REGEX = re.compile(r'^\[(.+)\]$')
CONTENT_INDENT_REGEX = re.compile(r'^(\s*).*__CONTENT__', re.MULTILINE)
BASE_NAME_REGEX = re.compile(r'\d+-\d+-[a-z]+-\d+-', re.MULTILINE)
WORDS_REGEX = re.compile(r'[-\w\'.]+')
TPL_HTML_FILE = Path('../_template.html')
INDEX_FILE = Path('data/index')
VOCAB_SIZE = 'md'


def get_file_args():
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


def run():
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
        content_indent = m.group(1) if m else ''

    with INDEX_FILE.open('r', encoding='utf-8') as f:
        try:
            value = f.read().strip()
            start_index = int(value)
        except ValueError as e:
            value = re.sub(r'\s+', ' ', value)
            print(f'Unable to parse index from index file: "{value}"')
            return
        index = start_index

    files = get_file_args()
    if not files:
        print(f'No .md or .html files found in input')
        return
    
    word_list = dict()
    for freq in ('low', 'med', 'high'):
        with Path(f'data/words-{freq}.txt').open('r', encoding='utf-8') as f:
            for word in f.read().splitlines():
                word_list[word] = freq
    
    nlp = spacy.load(f'en_core_web_{VOCAB_SIZE}')
    
    for file in files:
        print(f'-- Generating {file.stem} --')
        html_file = Path(f'../{file.stem}.html')
        data_file = Path(f'data-articles/{file.stem}.docx')
        is_new = not html_file.exists()
        
        if is_new:
            current_data = datetime.today().strftime('%d-%B-%Y').lower()
            slugged_name = SLUG_REGEX.sub('-', file.stem.strip().lower()).strip('-')
            output_name = f'{index:02d}-{current_data}-{slugged_name}'
            index += 1
        else:
            output_name = file.stem
        
        base_name = BASE_NAME_REGEX.sub('', output_name)

        image_path = Path(f'../img/{base_name}.jpg')
        if not image_path.exists():
            output_images = Path(f'../src/{base_name}.jpg')
            exported_images = parse_doc(data_file, output_images)
            if not exported_images:
                print(f'Could not find image "{image_path}" and no images to export from doc')
            else:
                extract_list = '", "'.join((f'{img.parent.name}/{img.name}'
                                            for img in exported_images))
                print(f'Images extracted for: "{extract_list}"')
            continue
        try:
            with Image.open(image_path) as img:
                img_width, img_height = img.size
        except Exception as e:
            print(f'Unable to open image: "{str(image_path)}"')
            img_width, img_height = 1200, 1200
        
        # Read data
        props = parse_doc(data_file)
        
        # Validate properties
        for name in ['title', 'description', 'difficulty', 'content']:
            if props[name] is None:
                print(f'"{name}" property not found')
                props[name] = ''

        content_text = props['content']
        
        props['title'] = titlecase(props['title'])
        props['description'] = props['description'].rstrip('.')
        props['word_count'] = str(len(
            WORDS_REGEX.findall(props['description'] + '\n' + content_text)))

        props['image'] = base_name
        props['preview'] = props['preview'] if not props['image'] else f'{base_name}_preview'

        # Highlight IELTS words
        parsed_text = ''
        search_index = 0
        doc = nlp(content_text)
        
        for token in doc:
            word_text: str = token.orth_
            upos = token.pos_
            lemma = str(token.lemma_).lower()
            next_index = content_text.find(word_text, search_index)
            # print(word_text, upos, lemma)
    
            # Should not get here
            if next_index == -1:
                print(f'Could not locate token "{word_text}" in content??')
                parsed_text = content_text
                search_index = len(content_text)
                break
    
            parsed_text += content_text[search_index:next_index]
    
            if word_text in word_list:
                word_freq = word_list[word_text]
                lemma = None
            elif lemma in word_list:
                word_freq = word_list[lemma]
            else:
                word_freq = None
                lemma = None
            
            if word_freq:
                if lemma is not None:
                    lemma = f' data-lemma="{lemma}"'
                else:
                    lemma = ''
                parsed_text += f'<span class="word {word_freq}"{lemma} tabindex="-1">' \
                               f'{word_text}</span>'
            else:
                parsed_text += word_text
    
            search_index = next_index + len(word_text)
            pass

        if search_index < len(content_text):
            parsed_text += content_text[search_index]
        content_text = parsed_text

        content_text = content_text.replace('\n\n', f'</p>\r{content_indent}<p>')
        content_text = content_text.replace('\n', f'\n{content_indent}\t<br>')
        content_text = content_text.replace('\r', '\n')
        props['content'] = '<p>' + content_text + '</p>'

        props['img_width'] = str(img_width)
        props['img_height'] = str(img_height)
        
        # Do substitutions
        output_html = tpl_data
        for key, value in props.items():
            key = f'__{key.upper()}__'
            output_html = output_html.replace(key, value)
        
        # Output
        with Path(f'../{output_name}.html').open('w', encoding='utf-8') as f:
            f.write(output_html)

        if is_new:
            file.rename(file.with_name(f'{output_name}.docx'))
        
        # Update index
        if index != start_index:
            with INDEX_FILE.open('w', encoding='utf-8') as f:
                f.write(str(index))
    pass


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        traceback.print_exc()
    
    if 'PYCHARM_HOSTED' not in os.environ:
        print('Press any key to exit.')
        input()
