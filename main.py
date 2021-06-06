from io import FileIO
import nltk
import os
from collections import OrderedDict
from bs4 import BeautifulSoup
from nltk.stem import SnowballStemmer
from nltk.corpus import stopwords


class InvertedIndex:

    def __init__(self):
        nltk.download('stopwords')

        nltk.download('words')

        self.stemmer = SnowballStemmer(language='english')
        self.stoplist = stopwords.words("english")
        self.tokenizer = nltk.RegexpTokenizer(r'\w+')

        self.folders = {}
        self.fileid = 1

    def add_folder(self, id, folder):
        self.folders[id] = folder

    def add_file(self, docID, path, length, mag):
        with open('docinfo.txt', 'a') as f:
            f.write(str(docID) + ',' + path + ',' + str(length) + ',' + str(mag) + '\n')

    def clear_docinfo(self):
        with open('docinfo.txt', 'w') as f:
            pass

    def parse_file(self, tokens, text, fileid):
        toks = self.tokenizer.tokenize(text)
        toks_file = {}
        tok_n = 0
        for token in toks:
            tok_n += 1
            if token not in self.stoplist:
                stem = self.stemmer.stem(token).lower()
                if stem not in toks_file:
                    toks_file[stem] = []
                toks_file[stem].append(tok_n)

        for k, v in toks_file.items():
            if k not in tokens:
                tokens[k] = {}
            tokens[k][fileid] = v
        return tok_n

    def create_index(self, folderpath, id):
        self.add_folder(id, folderpath)

        i = 0
        tokens = {}
        files = os.listdir(folderpath)
        for file in files:
            filepath = folderpath + "/" + file
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as file:
                soup = BeautifulSoup(file.read(), 'html.parser')
                text = soup.text.lower()
                if text is None:
                    continue
                temp = self.parse_file(tokens, text, self.fileid)
                self.add_file(self.fileid, filepath, temp, 0)
                self.fileid += 1
                i += 1
                if i > 10:
                    break

        tokens = OrderedDict(sorted(tokens.items()))
        self.save_index(tokens, id)

    def save_index(self, tokens, id):
        with open('index_' + str(id) + '_terms.txt', 'w') as terms:
            with open('index_' + str(id) + '_postings.txt', 'w') as postings:

                byte_offset = 0
                for token, value in tokens.items():
                    out = str(len(value))
                    del_file = 0
                    for k, v in value.items():
                        out += ' ' + str(k - del_file) + ' ' + str(len(v))
                        del_pos = 0
                        for pos in v:
                            out += ' ' + str(pos - del_pos)
                            del_pos = pos
                        del_file = k
                    out += '\n'

                    try:
                        terms.write(token + '\t' + str(byte_offset) + '\n')
                        postings.write(out)
                    except Exception as e:
                        pass

                    byte_offset += len(out) + 1

    def get_token_offset(self, term, filename):
        with open(filename) as terms:
            for line in terms:
                token, offset = line.split('\t')
                if term == token:
                    return int(offset)
        return -1

    def search_word(self, word, term_f='index_terms.txt', postings_f='index_postings.txt'):

        stem = self.stemmer.stem(word)

        offset = self.get_token_offset(stem, term_f)
        if offset == -1:
            print("Not Found")
            return

        posting = ''
        with open(postings_f) as f_posting:
            f_posting.seek(offset)
            posting = f_posting.readline()

        postings = posting.split(' ')
        postings = list(map(int, postings))

        print('Term:', word)
        print('Stem:', stem)

        prev_file = 0
        x = 1
        for i in range(postings[0]):
            file_id = prev_file + postings[x]
            x += 1
            print('DocID:', file_id)
            prev_off = 0
            for j in range(postings[x]):
                x += 1
                offset = prev_off + postings[x]
                print(offset, end=' ')
                prev_off = offset

            print()
            prev_file = file_id
            x += 1

    def merge_postings(self, posting1, posting2):
        postings1 = posting1.split(' ')
        postings2 = posting2.split(' ')

        postings1 = list(map(int, postings1))
        postings2 = list(map(int, postings2))

        i = 0
        j = 0
        n = postings1[0]
        m = postings2[0]

        prev_file = 0
        x = 1
        for i in range(postings1[0]):
            file_id = prev_file + postings1[x]
            x += 1
            for j in range(postings1[x]):
                x += 1
            prev_file = file_id
            x += 1

        postings2[1] = postings2[1] - prev_file

        out = str(n + m)
        for p in postings1[1:]:
            out += ' ' + str(p)
        for p in postings2[1:]:
            out += ' ' + str(p)
        out += '\n'

        return out

    def merge_indexes(self, f_terms1, f_postings1, f_terms2, f_postings2, f_terms, f_postings):
        terms1 = open(f_terms1, 'r')
        postings1 = open(f_postings1, 'r')
        terms2 = open(f_terms2, 'r')
        postings2 = open(f_postings2, 'r')

        with open(f_terms, 'w') as terms:
            with open(f_postings, 'w') as postings:
                byte_offset = 0
                term1 = terms1.readline()
                term2 = terms2.readline()
                posting1 = postings1.readline()
                posting2 = postings2.readline()
                while term1 != '' or term2 != '':
                    out = ''
                    token = None
                    tok1 = term1.split('\t')[0]
                    tok2 = term2.split('\t')[0]
                    if tok1 == tok2:
                        token = tok1
                        out = self.merge_postings(posting1, posting2)
                        term1 = terms1.readline()
                        term2 = terms2.readline()
                        posting1 = postings1.readline()
                        posting2 = postings2.readline()
                    elif term1 == '' or (term2 != '' and tok2 < tok1):
                        token = tok2
                        out = posting2
                        term2 = terms2.readline()
                        posting2 = postings2.readline()
                    elif term2 == '' or (term1 != '' and tok1 < tok2):
                        token = tok1
                        out = posting1
                        term1 = terms1.readline()
                        posting1 = postings1.readline()

                    try:
                        terms.write(token + '\t' + str(byte_offset) + '\n')
                        postings.write(out)
                    except Exception as e:
                        print(e)
                    byte_offset += len(out) + 1

        terms1.close()
        postings1.close()
        terms2.close()
        postings2.close()


def main():
    index = InvertedIndex()
    index.clear_docinfo()
    index.create_index('corpus1/1', 1)
    index.create_index('corpus1/2', 2)
    index.create_index('corpus1/3', 3)
    index.merge_indexes('index_1_terms.txt', 'index_1_postings.txt', 'index_2_terms.txt', 'index_2_postings.txt',
                        'index_12_terms.txt', 'index_12_postings.txt')
    index.merge_indexes('index_12_terms.txt', 'index_12_postings.txt', 'index_3_terms.txt', 'index_3_postings.txt',
                        'index_terms.txt', 'index_postings.txt', )
    index.search_word('yes')


if __name__ == '__main__':
    main()
