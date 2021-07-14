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


def to_bool(value):
    value = str(value).lower()
    
    if value == 'true' or value == '1':
        return True
    return False


PROP_CONVERSIONS = dict(
    preview=to_bool,
)


class ParseMode(Enum):
    Properties = 1
    Content = 2


def parse_doc(path, export_images: Path = None):
    zip_file = ZipFile(path)
    pprint(zip_file.namelist())
    
    rels_text = zip_file.read('word/_rels/document.xml.rels').decode('utf-8')
    rels = BeautifulSoup(rels_text, 'xml')
    
    image_paths = dict()
    
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
        image_paths[r_id] = r_path
        
        if export_images is not None:
            rel_file = Path(r_path)
            if is_first_image:
                output_file = export_images.with_name(
                    f'{export_images.stem}{rel_file.suffix}')
            else:
                output_file = export_images.with_name(
                    f'{export_images.stem}__{r_id}{rel_file.suffix}')
            
            i = 1
            while output_file.exists():
                output_file = output_file.with_name(
                    f'{output_file.stem}_{i:02d}{output_file.suffix}')
            
            exported_images.append(output_file)
            with output_file.open('wb') as f:
                f.write(zip_file.read(r_path.lstrip('/')))
                pass
            pass
        pass
    
    if export_images:
        return exported_images

    doc_text = zip_file.read('word/document.xml').decode('utf-8')
    doc = BeautifulSoup(doc_text, 'xml')
    body = doc.body
    
    if not body:
        return None

    mode = ParseMode.Properties
    props = dict(
        title=None,
        description=None,
        preview=False,
        difficulty='Medium',
        content=None,
    )
    content = []

    for p in doc.find_all('w:p'):
        text = get_text(p).strip()
        
        style_tag = p.find('pStyle')
        style = style_tag['w:val'] if style_tag and style_tag.has_attr('w:val') else 'Normal'
        
        if mode == ParseMode.Properties:
            if not text:
                continue
                
            if style == 'Heading1':
                props['title'] = text
            elif style == 'Subtitle':
                props['description'] = text
            elif style == 'ListParagraph':
                key, value = re.match(r'(?:\s*(.+)\s*:)?\s*(.+)\s*', text).groups()
                
                if key is not None:
                    key = key.lower()
                    if key in props:
                        if key in PROP_CONVERSIONS:
                            value = PROP_CONVERSIONS[key](value)
                        props[key] = value
                    else:
                        print(f'Unknown property "{key}"')
                else:
                    pass
            else:
                mode = ParseMode.Content
            pass
        
        if mode == ParseMode.Content:
            if style == 'Heading2':
                break

            # image = p.find('pic')
            # 
            # if image and image.blipFill and image.blipFill.blip:
            #     blip = image.blipFill.blip
            #     if blip.has_attr('r:embed'):
            #         r_id = blip['r:embed']
            #         print('embed', r_id)
            #         pass
            #     continue
            
            if text:
                content.append(text)
            pass
    
    props['content'] = '\n'.join(content)
    
    # pprint(props)
    return props


def get_text(tag: Tag):
    output = []
    skip_next_newline = False
    
    for r in tag.find_all('w:r'):
        for child in r.contents:
            if child.name == 't':
                output.append(str(child.string))
                skip_next_newline = False
            elif child.name == 'br':
                if not skip_next_newline:
                    output.append('\n')
                skip_next_newline = True
    
    return ''.join(output)


def run():
    parse_doc(sys.argv[1])
    pass


if __name__ == '__main__':
    run()
