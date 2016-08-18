from DataLoading import ServerQuery, IAA


def main():
    # Get filled fields from LabKey
    annotations = ServerQuery.get_annotations_from_server()

    # TODO -- filter for batch 0 job ids
    '''
    # by job run ID
    right_job_id_fields = [f for f in all_fields[ROWS] if f[REPORT_JOB_ID] in IAA_JOB_IDS]
    '''

    # Reformat data structure for IAA
    iaa_annotations, num_of_annotators = restructure_annotations_for_iaa(annotations)

    # Find inter-annotator agreement
    IAA.calculate_iaa(iaa_annotations, num_of_annotators)


def restructure_annotations_for_iaa(annotations):
    iaa_annotations = {}
    num_of_annotators = len(annotations.keys())

    for annotator in annotations:
        for mrn in annotations[annotator]:
            for doc in annotations[annotator][mrn]:
                add_events(iaa_annotations, doc, annotator, annotations[annotator][mrn][doc])

    return iaa_annotations, num_of_annotators


def add_events(iaa_annotations, doc, annotator, events):
    if doc not in iaa_annotations:
        iaa_annotations[doc] = {}

    iaa_annotations[doc][annotator] = events


if __name__ == '__main__':
    main()
