from pathlib import Path

import numpy


def run():
    frequencies = dict()
    with Path(f'data/english-word-frequency.txt').open('r', encoding='utf-8') as f:
        lines = f.read().splitlines()
    for line in lines:
        word, freq = line.split('\t')
        frequencies[word.strip()] = int(freq.strip())
    
    for word_list_type in ('cet4', 'cet6'):
        output_words = []
        with Path(f'data/_{word_list_type}-vocabularyshop.com.txt')\
                .open('r', encoding='utf-8') as f:
            lines = f.read().splitlines()
        for line in lines:
            word = line.split('\t')[0].strip().lower()
            if word not in frequencies:
                print(word)
                continue
            output_words.append((word, frequencies[word]))
            pass

        output_words.sort(key=lambda x: x[1])
        split_freq = numpy.array_split([word for word, freq in output_words], 4)
        low = list(split_freq[0]) + list(split_freq[1])
        med = list(split_freq[2])
        high = list(split_freq[3])
        
        for word_list, freq in ((low, 'low'), (med, 'med'), (high, 'high')):
            with Path(f'data/words-{word_list_type}-{freq}.txt')\
                    .open('w', encoding='utf-8') as f:
                f.write('\n'.join(word_list))
    pass


if __name__ == '__main__':
    run()
