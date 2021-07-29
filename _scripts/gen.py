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
- pip install spacy (See full installation instructions: https://spacy.io/usage)
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

from gen_docx import parse_doc

TEST_DOC_PARSE = False
if TEST_DOC_PARSE:
    import spacy

SLUG_REGEX = re.compile(r'\W+')
PROP_REGEX = re.compile(r'^\[(.+)\]$')
CONTENT_INDENT_REGEX = re.compile(r'^(\s*).*__CONTENT__', re.MULTILINE)
BASE_NAME_REGEX = re.compile(r'\d+-\d+-[a-z]+-\d+-', re.MULTILINE)
CONTENT_CLEAN_REGEX = (
    (re.compile(r'’'), '\''),
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
SLUG_TO_TITLE_REGEX = re.compile(r'-+')
IGNORE_LIST_SPLIT_REGEX = re.compile(r'\s+')
TERM_SPLIT_REGEX = re.compile(r'[-–\s]+')
HYPEN_REGEX = re.compile(r'^[-–]+$')
ARTICLE_INDEX_LIST_END_REGEX = re.compile(r'([ \t]*)(<!-- __LIST_END__ -->)')

TPL_HTML_FILE = Path('../_template.html')
INDEX_FILE = Path('data/index')
ARTICLE_INDEX_FILE = Path('../articles.html')

VOCAB_SIZE = 'sm'

token_properties = dict()
token_offset = 0


def parse_token_properties(m):
    global token_properties, token_offset
    token_index = m.start() + token_offset
    token_properties[token_index] = m.group(1).strip(',').split(',') if m.group(1) else ['ignore']

    token_offset -= len(m.group(0)) - len(m.group(2))
    return m.group(2)


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


def run():
    global token_properties, token_offset
    
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
            value = f.read().strip().split('\n')
            start_index, last_file = int(value[0]), value[1].strip() if len(value) > 1 else ''
            start_last_file = last_file
        except ValueError:
            value = re.sub(r'\s+', ' ', value[0])
            print(f'Unable to parse index from index file: "{value}"')
            return
        index = start_index
        
    files = get_file_args(last_file)
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
    
    if TEST_DOC_PARSE:
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
        except Exception:
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
        for regex, sub in CONTENT_CLEAN_REGEX:
            content_text = regex.sub(sub, content_text)
        token_properties.clear()
        token_offset = 0
        content_text = TOKEN_PROPERTY_REGEX.sub(parse_token_properties, content_text)
        
        props['title'] = titlecase(props['title'].lower())
        props['description'] = props['description'].rstrip('.')
        
        words_text = props['description'] + '\n' + content_text
        for regex, sub in WORDS_CLEAN_REGEX:
            words_text = regex.sub(sub, words_text)
        split_words = WORDS_REGEX.findall(words_text)
        props['word_count'] = str(len(split_words))
        # pprint(split_words)

        props['image'] = base_name
        props['preview'] = props['image'] if not props['preview'] else f'{base_name}-preview'
        props['image_class'] = []
        if props['image_align']:
            props['image_class'].append('align-' + props['image_align'])
        del props['image_align']
        props['image_class'] = ' '.join(props['image_class'])
        if props['image_class']:
            props['image_class'] = ' ' + props['image_class']
            
        if not TEST_DOC_PARSE:
            continue

        # Highlight IELTS words
        parsed_text = ''
        prev_index = 0
        doc = nlp(content_text)
        
        ignore_words = IGNORE_LIST_SPLIT_REGEX.split(props['ignore']) if 'ignore' in props else []
        ignore_words = set([word.lower() for word in ignore_words])
        
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
            token_props = token_properties[token_index] if token_index in token_properties else []
            
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
                has_whitespace = any(
                    [bool(has_whitespace) for _, has_whitespace, term_token in sub_terms[:-1]])
                sub_terms_strs = [term_token.orth_.lower() for _, _, term_token in sub_terms]

                for delimiter in (' ', '-'):
                    require_whitespace = delimiter == ' '
                    # Don't allow shitespace beteen hyphens
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

            parsed_text += content_text[prev_index:token_index]

            word_freq = None
            data_lemma = None
            
            if word_text.lower() not in ignore_words and 'ignore' not in token_props:
                if word_text in word_list:
                    word_freq = word_list[word_text]
                elif lemma in word_list:
                    word_freq = word_list[lemma]
                    data_lemma = lemma
            
            if word_freq:
                if data_lemma is not None:
                    data_lemma = f' data-lemma="{data_lemma}"'
                else:
                    data_lemma = ''
                
                word_lists = ' '.join(list_type for list_type, freq in word_freq)
                freqs = (' ' + ' '.join(f'{list_type}-{freq}' for list_type, freq in word_freq if freq)).rstrip()
                parsed_text += f'<span class="word {word_lists}{freqs}"{data_lemma} tabindex="-1">' \
                               f'{word_text}</span>'
            else:
                parsed_text += word_text
    
            prev_index = token_index + len(word_text)
            pass

        if prev_index < len(content_text):
            parsed_text += content_text[prev_index]
        content_text = parsed_text

        content_text = content_text.replace('\n\n', f'</p>\r{content_indent}<p>')
        content_text = content_text.replace('\n', f'\n{content_indent}\t<br>')
        content_text = content_text.replace('\r', '\n')
        props['content'] = '<p>' + content_text + '</p>'

        props['img_width'] = str(img_width)
        props['img_height'] = str(img_height)
        
        # These properties should not substituted in the template
        for key in ('ignore', ):
            if key in props:
                del props[key]
        
        # Do substitutions
        output_html = tpl_data
        for key, value in props.items():
            key = f'__{key.upper()}__'
            output_html = output_html.replace(key, value)
        
        # Output
        with Path(f'../{output_name}.html').open('w', encoding='utf-8') as f:
            f.write(output_html)

        if is_new:
            file = file.rename(file.with_name(f'{output_name}.docx'))
            last_file = str(file)
            add_to_index(output_name, base_name)

    # Update index
    if index != start_index or last_file != start_last_file:
        with INDEX_FILE.open('w', encoding='utf-8') as f:
            f.write('\n'.join([str(index), last_file]))
    pass


def add_to_index(output_name, base_name):
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
    new_item = f'{indent}<li><a href="{output_name}.html">{titlecase(base_name)}</a></li>'
    start, end = m.start(), m.end()
    text = text[:start] + f'{new_item}\n{indent}{m.group(2)}' + text[end:]
    
    with ARTICLE_INDEX_FILE.open('w', encoding='utf-8') as f:
        f.write(text)
    pass


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        traceback.print_exc()
    
    if 'PYCHARM_HOSTED' not in os.environ:
        print('Press any key to exit.')
        input()
