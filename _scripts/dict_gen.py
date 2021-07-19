import json
import re
from pathlib import Path
from pprint import pprint

DEFINITION_REGEX = re.compile(r'^([a-z]+\.)\s*(.+)')
DEFINITION_TYPE_ORDER = (
    'n', 'v', 'aux', 'pron', 'adj', 'adv', 'num', 'ad', 'conj',
    'prep', 'int', 'det', '-')


def run():
    dictionary = dict()
    types = set()
    
    path = Path(f'data/dict_full.txt')
    
    if not path.exists():
        print('Cannot find dictionary fil')
        return
    
    with path.open('r', encoding='utf-8') as f:
        for line in f.read().splitlines():
            words, definitions = line.split('\t')
            words = words.lower().strip().strip('|').split('|')
            definitions = definitions.replace('\\n', '\n')
            definitions = definitions.split('\n')
            
            base_word = words[0]
            output = dict()
            dictionary[base_word] = output

            for definition in definitions:
                definition = definition.strip()
                match = DEFINITION_REGEX.match(definition)
                if not match:
                    pos = '-'
                else:
                    pos = match.group(1).replace('.', '')
                    definition = match.group(2)
    
                types.add(pos)
    
                definition = definition.split('，')
    
                if pos not in output:
                    output[pos] = definition
                else:
                    for single_def in definition:
                        if single_def not in output[pos]:
                            output[pos].append(single_def)
                    pass
            
            for word in words[1:]:
                if word in dictionary:
                    print(f'Word variant "{word}" already exists in dictionary')
                    continue
                dictionary[word] = f'>{base_word}'
    
    # print(types)
    
    filtered_dict = dict()
    for list_type in ('cet4', 'cet6', 'ielts'):
        for freq in ('low', 'med', 'high'):
            with Path(f'data/words-{list_type}-{freq}.txt').open('r', encoding='utf-8') as f:
                for word in f.read().splitlines():
                    if word not in dictionary:
                        print(f'{word}')
                        # print(f'"{word}" not found in dictionary')
                        continue

                    filtered_dict[word] = dictionary[word]
        pass

    # pprint(filtered_dict)
    
    output_dict = dict()
    max_index = len(DEFINITION_TYPE_ORDER)
    for word, definition_types in filtered_dict.items():
        if isinstance(definition_types, str) and definition_types[0] == '>':
            output_dict[word] = definition_types
            continue
        
        items = []
        for def_type, value in definition_types.items():
            if def_type == '-':
                index = max_index + 1
            else:
                try:
                    index = DEFINITION_TYPE_ORDER.index(def_type)
                except:
                    index = max_index
            value = '，'.join(value)
            items.append((index, f'{def_type}\t{value}'))
        
        items.sort(key=lambda x: x[0])
        output_dict[word] = '\n'.join((defs for _, defs in items))
        pass
    
    # pprint(output_dict)
    
    with Path(f'../script/dict.js').open('w', encoding='utf-8') as f:
        contents = json.dumps(output_dict, ensure_ascii=False)
        contents = contents\
            .replace('", "', '","')\
            .replace('": "', '":"')
        contents = re.sub(r'"([a-z0-9_]+)":', r'\1:', contents)
        f.write(f'const DICT = {contents};')


if __name__ == '__main__':
    run()
