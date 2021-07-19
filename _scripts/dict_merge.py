import re
from pathlib import Path
from pprint import pprint

DEFINITION_REGEX = re.compile(r'^([a-z]+\.)\s*(.+)')
DEFINITION_TYPE_ORDER = (
    'n', 'v', 'aux', 'pron', 'adj', 'adv', 'num', 'ad', 'conj',
    'prep', 'int', 'det', '-')


def run():
    dictionary = dict()
    def_list = []
    types = set()
    
    index = 1
    while True:
        path = Path(f'data/dict_full_{index}.txt')
        index += 1
        
        if not path.exists():
            break
        
        with path.open('r', encoding='utf-8') as f:
            for line in f.read().splitlines():
                word_list, raw_definitions = line.split('\t')
                word_list = word_list.lower().strip().strip('|').split('|')
                words = set(word_list)
                raw_definitions = raw_definitions.replace('\\n', '\n')
                raw_definitions = raw_definitions.split('\n')
                
                word_data = None
                
                for word in words:
                    if word in dictionary:
                        word_data = dictionary[word]
                        break
                
                if not word_data:
                    word_data = (words, dict())
                    def_list.append(word_data)
                else:
                    word_data[0].union(words)
                
                for word in words:
                    dictionary[word] = word_data
                
                definitions = word_data[1]
                
                for definition in raw_definitions:
                    definition = definition.strip()
                    match = DEFINITION_REGEX.match(definition)
                    if not match:
                        pos = '-'
                    else:
                        pos = match.group(1).replace('.', '')
                        definition = match.group(2)
                    
                    types.add(pos)
                    definition = definition.split('，')
                    
                    if pos not in definitions:
                        definitions[pos] = definition
                    else:
                        for single_def in definition:
                            if single_def not in definitions[pos]:
                                definitions[pos].append(single_def)
                        pass

    # print(types)
    # pprint(dictionary)

    def_list.sort(key=lambda x: next(iter(x[0])))
    
    output = []
    max_index = len(DEFINITION_TYPE_ORDER)
    for words, defs in def_list:
        items = []
        for def_type, value in defs.items():
            if def_type == '-':
                index = max_index + 1
            else:
                try:
                    index = DEFINITION_TYPE_ORDER.index(def_type)
                except:
                    index = max_index
            value = '，'.join(value)
            if def_type != '-':
                def_type = f'{def_type}. '
            else:
                def_type = ''
            
            items.append((index, f'{def_type}{value}'))
    
        items.sort(key=lambda x: x[0])
        word_str = '|'.join(words)
        def_str = '\\n'.join((defs[1] for defs in items))
        output.append(f'{word_str}\t{def_str}')
        pass
    
    with Path(f'data/dict_full.txt').open('w', encoding='utf-8') as f:
        f.write('\n'.join(output))


if __name__ == '__main__':
    run()
