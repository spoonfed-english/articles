"""
Usage:
- A new .dat file: Will generate a new html file, using the data and file name of the .dat file
  automatically prepending a new index and the date.
  Will rename the .dat file to match
- A .dat file with a corresponding html file: Will regenerate that html file
- A folder: Will generate/regenerate all .dat or html files

Requirements:
- pip install titlecase (https://pypi.org/project/titlecase/)
"""
import re
import sys
from datetime import datetime
from pathlib import Path

from titlecase import titlecase

PROP_REGEX = re.compile(r'^\[(.+)\]$')
CONTENT_INDENT_REGEX = re.compile(r'^(\s*).*__CONTENT__', re.MULTILINE)
BASE_NAME_REGEX = re.compile(r'\d+-\d+-[a-z]+-\d+-', re.MULTILINE)
WORDS_REGEX = re.compile(r'[-\w\'.]+')
TPL_HTML_FILE = Path('_template.html')
INDEX_FILE = Path('data/_index')


def run():
    if not INDEX_FILE.exists():
        print(f'Cannot find index file: "{str(INDEX_FILE)}"')
        return
    if not TPL_HTML_FILE.exists():
        print(f'Cannot find template html file: "{str(TPL_HTML_FILE)}"')
        return
    
    if len(sys.argv) == 1:
        print('Nothing to do: Expected a single argument')
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
    
    path = Path(sys.argv[1])
    path.iterdir()
    files = [file for file in path.iterdir()
             if file.is_file() and file.suffix == '.md' and
             not file.name.startswith('_')] if path.is_dir()\
        else [path] if path.is_file() else None
    
    if files is None:
        print(f'"{str(path)}" does not exist')
        return
    
    if not files:
        print(f'No .md or .html files found in "{str(path)}"')
        return
    
    for file in files:
        print(f'-- Generating {file.stem} --')
        html_file = Path(f'{file.stem}.html')
        is_new = not html_file.exists()
        
        if is_new:
            current_data = datetime.today().strftime('%d-%B-%y').lower()
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
            difficulty=None,
            content=None,
        )
        with file.open('r', encoding='utf-8') as f:
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
        
        content_text = merge_lines(props['content'], '\n')
        
        # Process properties
        if props['image'] is None:
            props['image'] = [base_name]
        if props['preview'] is None:
            props['preview'] = props['image']
        for name in ['title', 'image', 'preview', 'description', 'difficulty']:
            props[name] = merge_lines(props[name])
        
        props['title'] = titlecase(props['title'])
        props['content'] = '<p>' + merge_lines(props['content'], f'</p>\n{content_indent}<p>') +\
                           '</p>'
        if props['content'][:len(content_indent)] == content_indent:
            props['content'] = props['content'][len(content_indent):]

        props['word_count'] = str(len(
            WORDS_REGEX.findall(props['description'] + '\n' + content_text)))
        
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
    return delimiter.join([line for line in lines if not ignore_empty or line.strip()])


if __name__ == "__main__":
    run()
