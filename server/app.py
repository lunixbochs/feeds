from flask import Flask, Response, abort, redirect, render_template, request
from flask_pymongo import PyMongo
import os

app = Flask('feeds')
app.config.update({
    'MONGO_URI': 'mongodb://localhost:27017/feeds',
    'SECRET_KEY': os.urandom(16).hex(),
})
if 'FLASK_SETTINGS' in os.environ:
    app.config.from_envvar('FLASK_SETTINGS')
mongo = PyMongo(app)

from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired

class ExampleForm(FlaskForm):
    text = StringField('text', validators=[DataRequired()])

# @app.route('/', methods=['GET', 'POST'])
@app.route('/')
def slash():
    obj = {'text': '', 'votes': 0}
    vote_obj = mongo.db.votes.find_one({'post_id': 1})
    if vote_obj: obj = vote_obj
    form = ExampleForm()
    form.text.data = obj['text']
    return render_template('index.html', obj=obj, form=form)

@app.route('/upvote', methods=['POST'])
def upvote():
    form = ExampleForm()
    if form.validate_on_submit():
        mongo.db.votes.find_one_and_update({'post_id': 1},
                                           {'$inc': {'votes': 1}, '$set': {'text': form.text.data}}, new=True, upsert=True)
    return redirect('/', code=302)

'''
@app.route('/p/<ObjectId:_id>.txt')
@app.route('/p/<_id>')
def get(_id):
    paste = mongo.db.paste.find_one_or_404({'_id': _id})
    return Response(paste['data'], mimetype='text/plain')
'''

if __name__ == '__main__':
    app.run(port=5005, debug=True)
