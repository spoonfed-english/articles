import json
import re
from pathlib import Path


def run():
    dictionary = dict()

    with Path(f'data/_dict_full.txt').open('r', encoding='utf-8') as f:
        for line in f.read().splitlines():
            word, definition = line.split('\t')
            dictionary[word] = definition
    
    output_dict = []
    output_dict1 = dict()
    for freq in ('low', 'med', 'high'):
        with Path(f'data/_words-{freq}.txt').open('r', encoding='utf-8') as f:
            for word in f.read().splitlines():
                if word not in dictionary:
                    print(f'"{word}" not found in dictionary')
                else:
                    output_dict1[word] = dictionary[word]
                    output_dict.append(f'{word}\t{dictionary[word]}')

        # with Path(f'data/_dict.txt').open('w', encoding='utf-8') as f:
        #     f.write('\n'.join(output_dict))
        with Path(f'script/dict.js').open('w', encoding='utf-8') as f:
            contents = json.dumps(output_dict1, ensure_ascii=False)
            contents = contents\
                .replace('", "', '","')\
                .replace('": "', '":"')
            contents = re.sub(r'"([a-z0-9_]+)":', r'\1:', contents)
            f.write(f'const DICT = {contents};')


if __name__ == '__main__':
    run()
