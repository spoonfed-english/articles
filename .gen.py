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
import re
import sys
from datetime import datetime
from pathlib import Path
from pprint import pprint

import nltk
from PIL import Image
from nltk import WordNetLemmatizer
from titlecase import titlecase

PROP_REGEX = re.compile(r'^\[(.+)\]$')
CONTENT_INDENT_REGEX = re.compile(r'^(\s*).*__CONTENT__', re.MULTILINE)
BASE_NAME_REGEX = re.compile(r'\d+-\d+-[a-z]+-\d+-', re.MULTILINE)
WORDS_REGEX = re.compile(r'[-\w\'.]+')
TPL_HTML_FILE = Path('_template.html')
INDEX_FILE = Path('data/index')


def run():
    if not INDEX_FILE.exists():
        print(f'Cannot find index file: "{str(INDEX_FILE)}"')
        return
    if not TPL_HTML_FILE.exists():
        print(f'Cannot find template html file: "{str(TPL_HTML_FILE)}"')
        return
    
    if len(sys.argv) == 1:
        print('Nothing to do: Expected one or more argument')
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

    files = []
    for arg in sys.argv[1:]:
        arg_path = Path(arg)
        is_file = arg_path.is_file()
        
        if not is_file and not arg_path.is_dir():
            print(f'Argument "{str(arg_path)}" is not a valid file or folder')
            continue

        if is_file and ():
            continue
        
        arg_files = arg_path.iterdir() if not is_file else (arg_path, )
        
        for file in arg_files:
            if not file.exists():
                continue
            if file.suffix != '.md' or file.name.startswith('_'):
                continue
            files.append(file)
            pass
    
    if not files:
        print(f'No .md or .html files found in input')
        return
    
    lemmatiser = WordNetLemmatizer()
    word_list = dict()
    for freq in ('low', 'med', 'high'):
        with Path(f'data/words-{freq}.txt').open('r', encoding='utf-8') as f:
            for word in f.read().splitlines():
                word_list[word] = freq
    
    for file in files:
        print(f'-- Generating {file.stem} --')
        html_file = Path(f'{file.stem}.html')
        data_file = Path(f'data-articles/{file.stem}.md')
        is_new = not html_file.exists()
        
        if is_new:
            current_data = datetime.today().strftime('%d-%B-%Y').lower()
            output_name = f'{index:02d}-{current_data}-{file.stem}'
            index += 1
        else:
            output_name = file.stem
        
        base_name = BASE_NAME_REGEX.sub('', output_name)
        
        # Read properties
        current_prop = None
        current_data = []
        props = dict(
            title=None,
            description=None,
            image=None,
            preview=None,
            difficulty=['Medium'],
            content=None,
        )
        with data_file.open('r', encoding='utf-8') as f:
            for line in f.read().splitlines():
                # Comment
                if len(line) > 0 and line[0] == '#':
                    continue
                # Check for a new property and store the previous one
                m = PROP_REGEX.match(line)
                if m:
                    push_prop(current_prop, current_data, props)
                    current_prop = m.group(1).strip()
                    current_data = []
                    continue
                
                current_data.append(line)
            # After processing all lines store any pending properties
            push_prop(current_prop, current_data, props)
            pass
        
        # Validate properties
        for name in ['title', 'description', 'difficulty', 'content']:
            if props[name] is None:
                print(f'"{name}" property not found')
                props[name] = ''
        
        # Process properties
        if props['image'] is None:
            props['image'] = [base_name]
        if props['preview'] is None:
            props['preview'] = props['image']
        for name in ['title', 'image', 'preview', 'description', 'difficulty']:
            props[name] = merge_lines(props[name])

        content_text = merge_lines(props['content'], '\n')
        
        props['title'] = titlecase(props['title'])
        props['word_count'] = str(len(
            WORDS_REGEX.findall(props['description'] + '\n' + content_text)))

        # Highlight IELTS words
        parsed_text = ''
        search_index = 0
        tokens = nltk.word_tokenize(content_text)
        for word in tokens:
            next_index = content_text.find(word, search_index)

            # The tokeniser converts starting quotes to `` and end quotes to ''
            if next_index == -1 and (word == '``' or word == "''"):
                next_index = content_text.find('"', search_index)
                if next_index != -1:
                    word = '"'
    
            # Should not get here
            if next_index == -1:
                print(f'Could not locate token "{word}" in content??')
                parsed_text = content_text
                search_index = len(content_text)
                break
    
            parsed_text += content_text[search_index:next_index]
    
            if word in word_list:
                word_freq = word_list[word]
                lemma = None
            else:
                lemma = lemmatiser.lemmatize(word)
                if lemma in word_list:
                    word_freq = word_list[lemma]
                else:
                    word_freq = None
            
            if word_freq:
                if lemma is not None:
                    lemma = f' data-lemma="{lemma}"'
                else:
                    lemma = ''
                parsed_text += f'<span class="word {word_freq}"{lemma} tabindex="-1">{word}</span>'
            else:
                parsed_text += word
    
            search_index = next_index + len(word)
            pass

        if search_index < len(content_text):
            parsed_text += content_text[search_index]
        content_text = parsed_text
        
        props['content'] = '<p>' +\
                           content_text.replace('\n', f'</p>\n{content_indent}<p>') + '</p>'

        image_name = props['image']
        image_path = Path(f'img/{image_name}.jpg')
        if not image_path.exists():
            print(f'Image does not exist: "{str(image_path)}"')
            continue
        try:
            with Image.open(image_path) as img:
                img_width, img_height = img.size
        except Exception as e:
            print(f'Unable to open image: "{str(image_path)}"')
            img_width, img_height = 1200, 1200

        props['img_width'] = str(img_width)
        props['img_height'] = str(img_height)
        
        # Do substitutions
        output_html = tpl_data
        for key, value in props.items():
            key = f'__{key.upper()}__'
            output_html = output_html.replace(key, value)
        
        # Output
        with Path(f'{output_name}.html').open('w', encoding='utf-8') as f:
            f.write(output_html)

        if is_new:
            file.rename(file.with_name(f'{output_name}.md'))
        
        # Update index
        if index != start_index:
            with INDEX_FILE.open('w', encoding='utf-8') as f:
                f.write(str(index))
    pass


def push_prop(prop_name, prop_data, props):
    if prop_name is None:
        return
    if prop_name not in props:
        print(f'Unknown property "{prop_name}"')
        return
    props[prop_name] = prop_data
    pass


def merge_lines(lines, delimiter=' ', ignore_empty=True):
    return delimiter.join([line.strip() for line in lines if not ignore_empty or line.strip()])


if __name__ == "__main__":
    run()
