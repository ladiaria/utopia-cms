#!/usr/bin/env python

import json

FILE_NAME = 'photologue_data.json'


def delete_tags():
    with open(FILE_NAME) as data_file:
        data = json.load(data_file)
        for item in data:
            if item['model'] == 'photologue.gallery' or item['model'] == 'photologue.photo':
                del item['fields']['tags']

    with open(FILE_NAME, 'w') as data_file:
        json.dump(data, data_file)


if __name__ == "__main__":
    delete_tags()
