import csv
import os
import re
import numpy as np
import pandas as pd
import operator
from collections import defaultdict
from normalizing import normalize
import pickle
import os

#-*- coding: utf-8 -*-
def loading_data(data_path, eng=True, num=True, punc=False):
    # data example : "title","content"
    # data format : csv, utf-8
    corpus = pd.read_table(data_path, sep=",", encoding="utf-8")
    corpus = np.array(corpus)
    title = []
    contents = []
    count = 0
    for doc in corpus:
        if count == 60000:
            break
        if type(doc[0]) is not str or type(doc[1]) is not str:
            continue
        if len(doc[0]) > 0 and len(doc[1]) > 0:
            tmptitle = normalize(doc[0], english=eng, number=num, punctuation=punc)
            tmpcontents = normalize(doc[1], english=eng, number=num, punctuation=punc)
            title.append(tmptitle)
            contents.append(tmpcontents)
            count += 1
    
    return title, contents

# word_to_ix, ix_to_word 생성
def make_dict(contents, minlength, maxlength, jamo_delete=False):
    dict = defaultdict(lambda: [])
    for doc in contents:
        for idx, word in enumerate(doc.split()):
            if len(word) > minlength:
                normalizedword = word[:maxlength]
                if jamo_delete:
                    tmp = []
                    for char in normalizedword:
                        if ord(char) < 12593 or ord(char) > 12643:
                            tmp.append(char)
                    normalizedword = ''.join(char for char in tmp)
                if word not in dict[normalizedword]:
                    dict[normalizedword].append(word)
    dict = sorted(dict.items(), key=operator.itemgetter(0))[1:]
    words = []
    for i in range(len(dict)):
        word = []
        word.append(dict[i][0])
        for w in dict[i][1]:
            if w not in word:
                word.append(w)
        words.append(word)

    words.append(['<PAD>'])
    words.append(['<S>'])
    words.append(['<E>'])
    words.append(['<UNK>'])
    # word_to_ix, ix_to_word 생성
    ix_to_word = {i: ch[0] for i, ch in enumerate(words)}
    with open("ix_to_word.pickle", "wb") as f:
        pickle.dump(ix_to_word, f)
    
    word_to_ix = {}
    for idx, words in enumerate(words):
        for word in words:
            word_to_ix[word] = idx
    with open("word_to_ix.pickle", "wb") as t:
        pickle.dump(word_to_ix, t)
    print("len ix_to_word",len(ix_to_word),"len word_to_ix",len(word_to_ix))
    

    print('contents number: %s, voca numbers: %s' %(len(contents),len(ix_to_word)))
    return word_to_ix,ix_to_word

def make_suffle(rawinputs, rawtargets, word_to_ix, encoder_size, decoder_size, shuffle=True):
    rawinputs = np.array(rawinputs)
    rawtargets = np.array(rawtargets)
    if shuffle:
        shuffle_indices = np.random.permutation(np.arange(len(rawinputs)))
        rawinputs = rawinputs[shuffle_indices]
        rawtargets = rawtargets[shuffle_indices]
    encoder_input = []
    decoder_input = []
    targets = []
    target_weights = []
    for rawinput, rawtarget in zip(rawinputs, rawtargets):
        tmp_encoder_input = [word_to_ix[v] for idx, v in enumerate(rawinput.split()) if idx < encoder_size and v in word_to_ix]
        encoder_padd_size = max(encoder_size - len(tmp_encoder_input), 0)
        encoder_padd = [word_to_ix['<PAD>']] * encoder_padd_size
        encoder_input.append(list(reversed(tmp_encoder_input + encoder_padd)))
        tmp_decoder_input = [word_to_ix[v] for idx, v in enumerate(rawtarget.split()) if idx < decoder_size - 1 and v in word_to_ix]
        decoder_padd_size = decoder_size - len(tmp_decoder_input) - 1
        decoder_padd = [word_to_ix['<PAD>']] * decoder_padd_size
        decoder_input.append([word_to_ix['<S>']] + tmp_decoder_input + decoder_padd)
        targets.append(tmp_decoder_input + [word_to_ix['<E>']] + decoder_padd)
        tmp_targets_weight = np.ones(decoder_size, dtype=np.float32)
        tmp_targets_weight[-decoder_padd_size:] = 0
        target_weights.append(list(tmp_targets_weight))
    return encoder_input, decoder_input, targets, target_weights

def doclength(docs,sep=True):
    max_document_length = 0
    for doc in docs:
        if sep:
            words = doc.split()
            document_length = len(words)
        else:
            document_length = len(doc)
        if document_length > max_document_length:
            max_document_length = document_length
    return max_document_length

def make_batch(encoder_inputs, decoder_inputs, targets, target_weights):
    encoder_size = len(encoder_inputs[0])
    decoder_size = len(decoder_inputs[0])
    encoder_inputs, decoder_inputs, targets, target_weights = np.array(encoder_inputs), np.array(decoder_inputs), np.array(targets), np.array(target_weights)
    result_encoder_inputs = []
    result_decoder_inputs = []
    result_targets = []
    result_target_weights = []
    for i in range(encoder_size):
        result_encoder_inputs.append(encoder_inputs[:, i])
    for j in range(decoder_size):
        result_decoder_inputs.append(decoder_inputs[:, j])
        result_targets.append(targets[:, j])
        result_target_weights.append(target_weights[:, j])
    return result_encoder_inputs, result_decoder_inputs, result_targets, result_target_weights

