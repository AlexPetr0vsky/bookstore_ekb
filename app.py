import requests
from bs4 import BeautifulSoup
from flask import *
from sqlalchemy import create_engine, exc
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import sessionmaker
from db_setup import Book, Author, Base, User
from flask_restful import reqparse, abort, Api, Resource
from flask_wtf import FlaskForm
from flask_login import *
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo
from config import Config
from werkzeug.urls import url_parse
from werkzeug.utils import secure_filename
from models import User


app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config.from_object(Config)
login = LoginManager(app)
login.login_view = 'login'
db = SQLAlchemy(app)
api = Api(app)


engine = create_engine('sqlite:///books.db?check_same_thread=False', echo=True)
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


@app.route('/')
def index():
    query = session.query(Book, Author)
    query = query.join(Author, Book.author_id == Author.id)
    query_all = query.all()
    query_list = []
    for book, author in query_all:
        books_dic = book.to_dict(only=('id', 'book', 'description', 'icon_book'))
        authors_dic = author.to_dict(only=('name', 'photo'))
        query_dic = books_dic | authors_dic
        query_list.append(query_dic)
    return render_template('index.html', books=query_list)


@app.route('/api/books', methods=['POST'])
def create_book():
    if not request.json:
        return jsonify({'error': 'Empty request'})
    elif not all(key in request.json for key in
                 ['book']):
        return jsonify({'error': 'Bad request'})
    author = Author(
        name=request.json['name'],
        photo=request.json['photo'],
        wiki=request.json['wiki']
    )
    author_id = session.query(Author.id).filter(Author.name == request.json['name'])
    book = Book(
        book=request.json['book'],
        description=request.json['description'],
        icon_book=request.json['icon_book'],
        author_id=author_id
    )
    session.add_all([author, book])
    session.commit()
    return jsonify({'success': 'OK'})


@app.route('/authors')
def get_authors():
    authors = session.query(Author).distinct(Author.name).all()
    return render_template('authors.html', authors=authors)


@app.route('/authors/<int:author_id>/about')
def authors_wiki(author_id):
    author = session.query(Author).filter_by(id=author_id).one()
    url = session.query(Author.wiki).filter_by(id=author_id).one()[0]
    response = requests.get(url)
    doc = BeautifulSoup(response.text, 'lxml')
    intro = doc.body.find(id='intro').text
    info = doc.body.find_all(class_="quickfactsdata tq")
    info_set = set()
    for i in info:
        i = i.text
        info_set.add(i)
    return render_template('about.html', author=author, about=intro, info=info_set)


@app.route('/contacts')
def contacts():
    return render_template('contacts.html')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


@login.user_loader
def load_user(id):
    return session.query(User).get(int(id))


@app.route('/sign_in', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = session.query(User).filter_by(name=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('sign_in.html', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = session.query(User).filter_by(name=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = session.query(User).filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(name=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


def abort_if_book_not_found(book_id):
    book = session.query(Book).get(book_id)
    if not book:
        abort(404, message="Book {book_id} not found".format(book_id))


class BookResource(Resource):
    def get(self, book_id):
        abort_if_book_not_found(book_id)
        book = session.query(Book).get(book_id)
        return jsonify(
                book.to_dict(only=('id', 'book'))
        )


@app.route('/book/<int:book_id>/<string:filename>', methods=['GET'])
def get_book(book_id, filename):
    book = session.query(Book).filter_by(id=book_id).one()
    return render_template('book.html', book=book, value=filename)


@app.route('/search/', methods=['GET'])
def search_book():
    try:
        book_name = request.args.get('book')
        books = session.query(Book).filter(Book.book.ilike("%{}%".format(book_name))).all()
        return render_template('search.html', books=books)
    except exc.NoResultFound:
        return render_template('search.html')


UPLOAD_FOLDER = 'static/files/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# @app.route('/uploadfile', methods=['GET', 'POST'])
# def upload_file():
#     if request.method == 'POST':
#         if 'file' not in request.files:
#             print('no file')
#             return redirect(request.url)
#         file = request.files['file']
#         if file.filename == '':
#             print('no filename')
#             return redirect(request.url)
#         else:
#             filename = secure_filename(file.filename)
#             file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
#             print("saved file successfully")
#             return redirect(url_for(get_book) + filename)
#     return render_template('upload_file.html')


@app.route('/return-file/<filename>')
def return_files(filename):
    try:
        file_path = UPLOAD_FOLDER + filename
        return send_file(file_path, as_attachment=True, download_name='')
    except FileNotFoundError:
        return 'Book not found! We are sorry!'


api.add_resource(BookResource, '/book/<int:book_id>')

