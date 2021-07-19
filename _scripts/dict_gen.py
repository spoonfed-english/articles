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
    
    index = 1
    while True:
        path = Path(f'data/dict_full_{index}.txt')
        index += 1
        
        if not path.exists():
            break
        
        i = 0
        with path.open('r', encoding='utf-8') as f:
            for line in f.read().splitlines():
                # i += 1
                # if i > 125:
                #     break
                words, definitions = line.split('\t')
                words = words.lower().strip().strip('|').split('|')
                definitions = definitions.replace('\\n', '\n')
                definitions = definitions.split('\n')
                
                for word in words:
                    if word not in dictionary:
                        output = dict()
                        dictionary[word] = output
                    else:
                        output = dictionary[word]
    
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
    
    # print(types)
    
    filtered_dict = dict()
    for list_type in ('cet4', 'cet6', 'ielts'):
        for freq in ('low', 'med', 'high'):
            with Path(f'data/words-{list_type}-{freq}.txt').open('r', encoding='utf-8') as f:
                for word in f.read().splitlines():
                    if word not in dictionary:
                        print(f'{word}')
                        # print(f'"{word}" not found in dictionary')
                    else:
                        filtered_dict[word] = dictionary[word]
        pass

    # pprint(filtered_dict)
    
    output_dict = dict()
    max_index = len(DEFINITION_TYPE_ORDER)
    for word, definition_types in filtered_dict.items():
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


def sort_by_type(x):
    def_type = x[0]
    if def_type == '-':
        return 99999
    
    return def_type


if __name__ == '__main__':
    run()
