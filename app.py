import os, json
from flask import Flask, escape, request, jsonify, g, flash, redirect, url_for, send_file
from werkzeug.utils import secure_filename
import sqlite3

UPLOAD_FOLDER = 'uploads/scantrons/'
ALLOWED_EXTENSIONS = {'json'}

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'super secret key'
app.config['SESSION_TYPE'] = 'filesystem'


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect('my_database.sqlite')
    return db


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.route('/')
def api_hello():
    if 'name' in request.args:
        return request.args['name']
    else:
        return 'API works!'

@app.route('/uploads/scantrons/<filename>',methods=['GET'])
def downloadFile(filename):
    path = os.path.join(UPLOAD_FOLDER, filename)
    return send_file(path, as_attachment=True)

@app.route('/api/tests', methods=['POST'])
def insert_tests():
    subject = request.json['subject']
    answer_keys = request.json['answer_keys']

    # print(answer_keys)
    a = 'INSERT INTO `subjects`("name") VALUES ("' + subject + '");'
    # print(a)
    conn = sqlite3.connect('my_database.sqlite')
    cur = conn.cursor()
    cur.execute(a)
    conn.commit()

    sub_id = 0
    for row in cur.execute('select seq from sqlite_sequence where name="subjects"'):
        sub_id = row[0]

    z = ''
    for k, v in answer_keys.items():
        z += 'INSERT INTO `answer_key`("subject_id","qno","answer") VALUES ({},{},"{}");'.format(sub_id, k, v)

    cur.executescript(z)
    conn.close()

    return jsonify(
        test_id=sub_id,
        subject=subject,
        answer_keys=answer_keys,
        submissions=[]
    ), 201


@app.route('/api/tests/<sub_id>/scantrons', methods=['POST'])
def get_id(sub_id):
    if 'data' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['data']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if file and allowed_file(file.filename):

        data = json.load(file)
        subject = data['subject']
        name = data['name']
        answer_keys = data['answers']

        a = 'INSERT INTO "submissions"("sub_id","subject","name","scantron_url") VALUES ({},"{}","{}",NULL);'.format(
            sub_id, subject, name)
        # print(a)
        conn = sqlite3.connect('my_database.sqlite')
        cur = conn.cursor()
        cur.execute(a)
        conn.commit()

        cur.execute('select seq from sqlite_sequence where name="submissions"')
        subm_id = cur.fetchone()[0]
        filename = str(subm_id) + '_' + secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        url= "http://127.0.0.1:5000/{}".format(UPLOAD_FOLDER)+filename

        z = ''
        for k, v in answer_keys.items():
            z += 'INSERT INTO `submitted_answers`("subject_id","qno","answer") VALUES ({},{},"{}");'.format(subm_id, k,
                                                                                                            v)

        # print(z)
        cur.executescript(z)
        conn.commit()

        score = 0
        check = {}
        for i in range(1, 51):
            x = 'SELECT answer_key.qno, answer_key.`answer`,submitted_answers.answer FROM `answer_key`,`submitted_answers` WHERE (answer_key.subject_id={} AND submitted_answers.subject_id={} AND answer_key.qno={} AND submitted_answers.qno={});'.format(
                sub_id, subm_id, i, i)
            cur.execute(x)
            row = cur.fetchone()
            if isinstance(row, tuple):
                check.update({i: {"actual": row[1], "expected": row[2]}})
                if (row[1] == row[2]):
                    score += 1

        cur.execute('UPDATE submissions set score={},scantron_url="{}" WHERE id={}'.format(score, url, subm_id))
        conn.commit()
        conn.close()

        return jsonify(
            scantron_id=subm_id,
            scantron_url=url,
            name=name,
            subject=subject,
            score=score,
            result=check
        ), 201


@app.route('/api/tests/<sub_id>', methods=['GET'])
def get_sub(sub_id):
    conn = sqlite3.connect('my_database.sqlite')
    cur = conn.cursor()
    cur.execute('SELECT qno,answer from answer_key where subject_id={}'.format(sub_id))
    answer_key = cur.fetchall()

    cur.execute('SELECT name from subjects where id={}'.format(sub_id))
    name = cur.fetchone()[0]

    submissions = []
    cur.execute('SELECT id,name,subject,score,scantron_url from submissions where sub_id={}'.format(sub_id))
    rows = cur.fetchall()
    for row in rows:
        check = {
            'scantron_id': row[0],
            'scantron_url': row[4],
            "name": row[1],
            "subject": row[2],
            "score": row[3],
            "results": {}
        }

        for i in range(1, 51):
            x = 'SELECT answer_key.qno, answer_key.`answer`,submitted_answers.answer FROM `answer_key`,`submitted_answers` WHERE (answer_key.subject_id={} AND submitted_answers.subject_id={} AND answer_key.qno={} AND submitted_answers.qno={});'.format(
                sub_id, row[0], i, i)
            cur.execute(x)
            row1 = cur.fetchone()
            if isinstance(row1, tuple):
                check["results"].update({i: {"actual": row1[1], "expected": row1[2]}})

        submissions.append(check)

    conn.close()

    return jsonify(
        test_id=sub_id,
        subject=name,
        answer_keys=dict(answer_key),
        submissions=submissions
    ), 200
