import csv
from nltk.tokenize import *
from DataModeling.DataModels import Document, Event, Patient, Sentence
from SystemUtilities import Configuration
from SystemUtilities.Globals import *
from Extraction.KeywordSearch import KeywordSearch
from os import listdir
from os.path import isfile, join


def main(environment):
    if environment == Configuration.RUNTIME_ENV.TRAIN:
        print "Running in TRAINING environment with TRAINING data ..."
        print "Loading patient-level gold labels ..."
        patient_tob_gold_labels = Configuration.patients_all_gold_dir
        patient_alc_gold_labels = None

        print "Loading training document split ..."
        # dev_documents = load_split(Configuration.dev_csv)
        training_documents = load_split(Configuration.train_csv)
        # testing_documents = load_split(Configuration.test_csv)

        print "Loading training patient splits ..."
        # dev_patients = load_patients(dev_documents, patient_tob_gold_labels, patient_alc_gold_labels)
        training_patients = load_patients(training_documents, patient_tob_gold_labels, patient_alc_gold_labels)
        # testing_patients = load_patients(testing_documents, patient_tob_gold_labels, patient_alc_gold_labels)

        '''
        print "Loading sentence-level annotations ..."
        # Load Sentence-level annotations, if available
        sentence_level_annotations_dir = Configuration.flor_sentence_level_annotations_dir
        sent_ann_dict = load_sentence_annotations(sentence_level_annotations_dir)

        print "Setting sentence-level annotations ..."
        # Set sentence-level annotations
        #set_sentence_level_annotations(dev_patients, sent_ann_dict)
        set_sentence_level_annotations(training_patients, sent_ann_dict)
        #set_sentence_level_annotations(testing_patients, sent_ann_dict)
        '''

        return training_patients

    elif environment == Configuration.RUNTIME_ENV.EXECUTE:
        print "Running in EXECUTE environment with DEV data ..."
        print "Loading patient-level gold labels ..."
        patient_tob_gold_labels = Configuration.patients_all_gold_dir
        patient_alc_gold_labels = None

        print "Loading dev document splits ..."
        dev_documents = load_split(Configuration.dev_csv)

        print "Loading dev patient splits ..."
        dev_patients = load_patients(dev_documents, patient_tob_gold_labels, patient_alc_gold_labels)

        '''
        print "Loading sentence-level annotations ..."
        # Load Sentence-level annotations, if available
        sentence_level_annotations_dir = Configuration.flor_sentence_level_annotations_dir
        sent_ann_dict = load_sentence_annotations(sentence_level_annotations_dir)

        print "Setting sentence-level annotations ..."
        # Set sentence-level annotations
        set_sentence_level_annotations(dev_patients, sent_ann_dict)
        '''

        return dev_patients


'''
def set_sentence_level_annotations(patients, sent_ann_dict):
    for patient in patients:
        for doc in patient.doc_list:
            for sentence in doc.sent_list:
                if sentence.text.rstrip() in sent_ann_dict:
                    substype = sent_ann_dict[sentence].split("_")[0]
                    sent_label = sent_ann_dict[sentence][1]
                    evntObj = Event(substype)
                    evntObj.status = sent_label
                    sentence.predicted_events.append(evntObj)
    pass


def load_sentence_annotations(sentence_level_annotations_dir):
    sent_label_dict = dict()
    labels = {'C': "CURRENT", 'P': "PAST", 'U': "UNKNOWN", 'S': "SMOKER", "N": "NON", 'c': "CURRENT", 'p': "PAST",
              'u': "UNKNOWN", 's': "SMOKER", "n": "NON"}

    onlyfiles = [f for f in listdir(sentence_level_annotations_dir) if isfile(join(sentence_level_annotations_dir, f))]
    for subsType in onlyfiles:  # b/c sentence-level labels are organized into files by type (cig, alc, drug, etc)
        with open(sentence_level_annotations_dir + "\\" + f, "rb") as file:
            lines = file.readlines()
        for line in lines:
            tokens = line.split()
            label = tokens[0]
            sentence = line[2:]
            if label in labels:
                sent_label_dict[sentence.rstrip()] = subsType + "_" + labels[label]
    return sent_label_dict
'''


def read_csv(filepath):
    ID = "ID"
    TEXT = "TEXT"
    TOB_GOLD = "TOB_GOLD_LABEL"
    ALC_GOLD = "ALC_GOLD_LABEL"
    document_tuples = list()
    with open(filepath, "rb") as csv_file:
        note_reader = csv.reader(csv_file)
        line_number = 0
        for row in note_reader:  # each row is a document and its metadata
            if line_number == 0:  # its not the header
                headers = dict((k, v) for v, k in enumerate(row))
            else:
                note_text = row[headers.get(TEXT)]
                id = row[headers.get(ID)]
                tob_label = row[headers.get(TOB_GOLD)]
                alc_label = row[headers.get(ALC_GOLD)]
                document_tuples.append(tuple([id, note_text, tob_label, alc_label]))
            line_number += 1
    return document_tuples


def get_doc_sentences(doc):
    # Split sentences
    split_sentences, sent_spans = split_doc_text(doc.text)

    # Create sentence objects and stuff into doc
    sentence_object_list = list()
    for sent, span in zip(split_sentences, sent_spans):
        sent_obj = Sentence(doc.id, sent, span[0], span[1])
        sentence_object_list.append(sent_obj)

    # Assign doc's keywords to appropriate sentences
    assign_keywords_to_sents(sentence_object_list, doc)
    return sentence_object_list


def split_doc_text(text):
    sentences = sent_tokenize(text)
    spans = list(PunktSentenceTokenizer().span_tokenize(text))
    return sentences, spans


def assign_keywords_to_sents(sents, doc):
    for event in doc.gold_events:
        substance = event.substance_type
        doc_hits = doc.keyword_hits[substance]
        keyword_index = 0
        sent_index = 0

        # Iterate through both sentences and keywords
        while not(keyword_index == len(doc_hits) or sent_index == len(sents)):
            sent_start = sents[sent_index].span_in_doc_start
            sent_end = sents[sent_index].span_in_doc_end
            keyword_start = doc_hits[keyword_index].span_start
            keyword_end = doc_hits[keyword_index].span_end

            # If current keyword is past current sentence, go to next sentence
            if keyword_start > sent_end:
                sent_index += 1
            # If sentence is past keyword, go to next keyword
            elif sent_start > keyword_end:
                keyword_index += 1
            # Else, they overlap and keyword should be assigned to sentence
            else:
                sents[sent_index].keyword_hits[substance].append(doc_hits[keyword_index])
                keyword_index += 1


def load_split(split_csv_path):
    """ Returns a list of document objects for the given split """
    document_tuples = read_csv(split_csv_path)
    document_objs = list()

    keyword_regexes = {s: KeywordSearch.get_regex_from_file(s) for s in KEYWORD_SUBSTANCES}

    for tup in document_tuples:
        doc_id = tup[0]
        text = tup[1]
        tob_gold_label = tup[2]
        alc_gold_label = tup[3]
        doc = Document(doc_id, text)

        # Populate events
        if tob_gold_label != UNKNOWN:
            populate_event(doc, tob_gold_label, TOBACCO, keyword_regexes[TOBACCO])
        if alc_gold_label != UNKNOWN:
            populate_event(doc, alc_gold_label, ALCOHOL, keyword_regexes[ALCOHOL])

        # Populate doc sentences
        doc.sent_list = get_doc_sentences(doc)

        document_objs.append(doc)

    return document_objs


def populate_event(doc, gold_label, substance, regex):
    event = Event(substance)

    event.status = gold_label.rstrip()
    if event.status != "":
        doc.gold_events.append(event)

    load_doc_keywords(doc, substance, regex)


def load_doc_keywords(doc, substance, regex):
    hits = KeywordSearch.find_doc_hits(doc, regex)
    doc.keyword_hits[substance].extend(hits)


def load_patient_labels(patient_gold_labels_path):
    pid_label = dict()
    if patient_gold_labels_path is not None:
        with open(patient_gold_labels_path, "rb") as file:
            lines = file.readlines()
        for line in lines:
            id_label = line.split()
            pid_label[id_label[0]] = id_label[1]
    return pid_label


def load_patients(documents, patient_tob_gold_labels_path, patient_alc_gold_labels_path):
    """ Returns a list of patient objects populated with their respective documents """
    # Load gold labels
    pid__tob_goldLabel = load_patient_labels(patient_tob_gold_labels_path)
    pid__alc_goldLabel = load_patient_labels(patient_alc_gold_labels_path)

    # Build {patient : [docObj1, docObj2, ..,]} dictionary
    pid_listdocs_dict = dict()
    for doc in documents:
        pid = doc.id.split("-")[0]
        if pid in pid_listdocs_dict:
            pid_listdocs_dict[pid].append(doc)
        else:
            pid_listdocs_dict[pid] = list()
            pid_listdocs_dict[pid].append(doc)

    # Build list of patient objects
    patient_objects = list()
    for pid, doc_list in pid_listdocs_dict.iteritems():
        pat = Patient(pid)
        pat.doc_list = doc_list
        patient_objects.append(pat)

        if patient_tob_gold_labels_path is not None:
            # Populate Tobacco Events
            tob_event = Event("Tobacco")
            tob_event.status = pid__tob_goldLabel[pid].rstrip()
            if tob_event.status != "":
                pat.gold_events.append(tob_event)
        if patient_alc_gold_labels_path is not None:
            # Populate Alcohol Events
            alc_event = Event("Alcohol")
            alc_event.status = pid__alc_goldLabel[pid].rstrip()
            if alc_event.status != "":
                pat.gold_events.append(alc_event)
    return patient_objects


if __name__ == '__main__':
    main(Configuration.RUNTIME_ENV.TRAIN)
