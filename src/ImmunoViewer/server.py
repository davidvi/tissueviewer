from io import BytesIO
from collections import OrderedDict
from optparse import OptionParser
import os
from threading import Lock
import re
from unicodedata import normalize
import json
import cv2
import matplotlib.pyplot as plt
import numpy as np
import pathlib
from xml.etree import ElementTree as ET

from flask import Flask, render_template, Response, request, send_from_directory, send_file
from flask_cors import CORS, cross_origin

app = Flask(__name__)

cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
app.config['SLIDE_DIR'] = "/iv-store"
app.config['SAVE'] = True
app.config['COLORS'] = {
        'green': (0, 255, 0),
        'red': (0, 0, 255),
        'blue': (255, 0, 0),
        'yellow': (0, 255, 255),
        'cyan': (255, 255, 0),
        'magenta': (255, 0, 255),
        'white': (255, 255, 255),
        'black': (0, 0, 0),
    }
  

current_folder = pathlib.Path(__file__).parent.resolve()

def mix_channels(images, chs, gains):

    color_mapping = app.config['COLORS']

    merged_image = np.zeros((*images[0].shape, 3), dtype=np.uint8)

    for image, ch, gain in zip(images, chs, gains):
        color_rgb = color_mapping[ch]
        enhanced_image = cv2.convertScaleAbs(image, alpha=gain)
        colored_image = cv2.merge([enhanced_image * (color_rgb[i] // 255) for i in range(3)])
        merged_image = cv2.add(merged_image, colored_image)

    return merged_image

def find_directories_with_files_folders(base_dir):
    directories_with_files = []

    for root, dirs, files in os.walk(base_dir):
        if root.count(os.sep) - base_dir.count(os.sep) >= 2:
            del dirs[:]
        for dirname in dirs:
            if dirname.endswith("_files"):
                buf = {}
                buf['name'] = os.path.relpath(root, base_dir)
                dirs.sort()
                buf['files'] = dirs
                directories_with_files.append(buf)

                buf['details'] = {}

                if os.path.isfile(os.path.join(f'{root}','sample.json')):
                        with open(os.path.join(f'{root}','sample.json'), 'r') as f:
                            data = json.load(f)
                            buf['details'] = data
                break
    print(directories_with_files)
    return directories_with_files

def modify_dzi_format(dzi_file_path):
    with open(dzi_file_path, 'r') as file:
        dzi_content = file.read()

    tree = ET.ElementTree(ET.fromstring(dzi_content))
    root = tree.getroot()

    if root.attrib['Format'].lower() == 'tiff':
        root.attrib['Format'] = 'jpeg'

    modified_dzi_str = ET.tostring(root, encoding='unicode')
    
    return modified_dzi_str

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
@cross_origin()
def index(path):
    if path and (path.startswith('assets') or path.startswith('favicon') or path.startswith('images')):
        return send_from_directory(os.path.join(current_folder, "client"), path)
    else:
        return send_from_directory(os.path.join(current_folder, "client"), 'index.html')

@app.route('/samples.json')
@cross_origin()
def samples():
    file_json = find_directories_with_files_folders(os.path.abspath(app.config['SLIDE_DIR']))

    buf = {}
    buf['samples'] = file_json
    buf['save'] = app.config['SAVE']
    buf['colors'] = list(app.config['COLORS'].keys())

    resp = Response(json.dumps(buf), status=200, mimetype='application/json')
    return resp

@app.route('/<string:files>/<string:chs>/<string:gains>/<path:file>.dzi')
@cross_origin()
def dzi(files, chs, gains, file):
    files = files.split(';')
    path_to_dzi = os.path.join(os.path.abspath(app.config['SLIDE_DIR']), file, f'{files[0].replace("_files", "")}.dzi')
    dzi_content = modify_dzi_format(os.path.join(path_to_dzi))
    resp = Response(dzi_content, status=200, mimetype='application/xml')
    return resp

@app.route('/<string:files>/<string:chs>/<string:gains>/<path:file>_files/<int:level>/<string:loc>')
@cross_origin()
def tile(files, chs, gains, file, level, loc):
    loc = loc.replace('.jpeg', '.tiff')
    files = files.split(';') 
    chs = chs.split(';')
    gains = gains.split(';')
    gains = [int(x) for x in gains]

    if len(files) == 1:
        merged_image = cv2.imread(os.path.abspath(os.path.join(app.config['SLIDE_DIR'], file, f'{files[0]}', str(level), loc)))
    else:
        merge_images = []
        merge_chs = []
        merge_gains = []
        for i, ch in enumerate(chs):
            if ch != 'empty':
                buf = cv2.imread(os.path.abspath(os.path.join(app.config['SLIDE_DIR'], file, f'{files[i]}', str(level), loc)))
                buf = cv2.cvtColor(buf, cv2.COLOR_BGR2GRAY)
                merge_images.append(buf)
                merge_chs.append(ch)
                merge_gains.append(gains[i])

        if len(merge_images) == 0:
            merged_image = np.zeros((256, 256), dtype=np.uint8)
        else:
            merged_image = mix_channels(merge_images, merge_chs, merge_gains)

    img_bytes = cv2.imencode('.jpeg', merged_image)[1].tobytes()
    img_io = BytesIO(img_bytes)

    return send_file(img_io, mimetype='image/jpeg')

@app.route('/read/<path:file>')
@cross_origin()
def open_json(file):
    if os.path.isfile(os.path.abspath(os.path.join(app.config['SLIDE_DIR'], f'{file}.json'))):
        # Read the JSON file
        with open(os.path.abspath(os.path.join(app.config['SLIDE_DIR'], f'{file}.json')), 'r') as f:
            data = json.load(f)

    else: 
        data = {"notes": "", "name": "", "stains": ""}; 

    resp = Response(json.dumps(data), mimetype='application/json')
    return resp


@app.route('/save/<path:file>', methods=['GET', 'POST'])
@cross_origin()
def save_note(file):
    if request.method == 'POST' and app.config['SAVE']:
        data = json.loads(request.data)

        with open(os.path.abspath(os.path.join(app.config['SLIDE_DIR'], f'{file}', 'sample.json')), 'w') as f:
            json.dump(data, f)

        return "OK"
    else:
        return "SAVE BLOCKED"

def main():
    parser = OptionParser(usage='Usage: %prog [options] [folder]')

    parser.add_option(
        '-l',
        '--listen',
        metavar='ADDRESS',
        dest='host',
        default='0.0.0.0',
        help='address to listen on [0.0.0.0]',
    )
    parser.add_option(
        '-p',
        '--port',
        metavar='PORT',
        dest='port',
        type='int',
        default=5000,
        help='port to listen on [5000]',
    )
    parser.add_option(
        '-n', '--no-save',
        dest='save',
        action='store_false',
        default=True,
        help='disable saving user changes',
    )

    (opts, args) = parser.parse_args()

    try:
        app.config['SLIDE_DIR'] = args[0]
    except IndexError:
        if app.config['SLIDE_DIR'] is None:
            parser.error('No slide file specified')
            # app.config['SLIDE_DIR'] = "/iv-store"

    app.config['SAVE'] = opts.save

    print("save: ", app.config['SAVE'])

    app.run(host=opts.host, port=opts.port, threaded=True, debug=True)

if __name__ == '__main__':
    main()