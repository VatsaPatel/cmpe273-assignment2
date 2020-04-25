from flask import Flask, escape, request, jsonify, g
import sqlite3

id = 1001
c_id = 112200
students = {1001: 'Vatsa Patel', 1003: 'Vsrgatsa Patel',1006: 'Vasfgatsa Patel',1007: 'Vatsa Patel',}

classes = {1001: {'name': 'cmpe', 'students': []}}


# conn = sqlite3.connect('my_database.sqlite')
# cursor = conn.cursor()
# print("Opened database successfully")

app = Flask(__name__)

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

@app.route('/api/tests', methods=['POST'])
def insert_tests():
    subject = request.json['subject']
    answer_keys = request.json['answer_keys']

    # print(answer_keys)
    a = 'INSERT INTO `subjects`("name") VALUES ("' + subject + '");'
    print(a)
    conn = sqlite3.connect('my_database.sqlite')
    cur = conn.cursor()
    cur.execute(a)
    conn.commit()

    sub_id = 0
    for row in cur.execute('select seq from sqlite_sequence where name="subjects"'):
        sub_id = row[0]

        print(dict(answer_keys))
    # for k,v in answer_keys:
    #     z = 'INSERT INTO `answer_key`(subject_id","qno","asnwer") VALUES ({},{},{})'.format(sub_id,k,'v')
    #     print(z)
    # cur.execute(z)

    conn.close()

    # for user in query_db('select * from subjects'):
    #     print(user[0], 'has the id', user[1])


    return jsonify(
        user=sub_id,
        subject=subject,
        answer_keys=answer_keys,
    ), 201

@app.route('/students/<id>', methods=['GET'])
def get_id(id):
    return jsonify(
        id = id,
        name=students.get(int(id)),
    ), 200

@app.route('/classes/<id>', methods=['GET'])
def get_class(id):
    t=classes.get(int(id))
    return jsonify(
        id = id,
        name=t['name'],
        students=t['students']
    ), 200

@app.route('/classes', methods=['POST'])
def insert_class():
    name = request.json['name']
    global c_id
    c_id += 1
    classes[c_id] = { 'name': name, 'students': [] }
    print(classes)
    return jsonify(
        id = c_id,
        name=name,
        students= '[]'
    ), 201

@app.route('/classes/<class_id>', methods=['PATCH'])
def insert_studsent(class_id):
    stu_id = request.json['student_id']
    s_name = students.get(stu_id)
    classes[int(class_id)]['students'].append( {'id' : stu_id, 'name': s_name} )
    c_metadata = classes.get(int(class_id))
    print(c_metadata)
    return jsonify(
        id = class_id,
        name= c_metadata['name'],
        students= c_metadata['students']
    ), 201
