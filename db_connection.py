from flask import *
from sqlalchemy.ext.serializer import loads, dumps
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_setup import Book, Author, Base
from flask_restful import reqparse, abort, Api, Resource


app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
api = Api(app)


engine = create_engine('sqlite:///books.db?check_same_thread=False', echo=True)
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


def abort_if_book_not_found(book_id):
    book = session.query(Book).get(book_id)
    if not book:
        abort(404, message=f"Book {book_id} not found")


# remarque = Author(name='Remarque E.M.', photo='static/img/remarque.jpg')
# remarque.books = [Book(book="All Quiet on the Western Front", icon_book="static/img/all_quiet.jpg",
#                       description="Это рассказ о немецких мальчишках, которые под действием патриотической пропаганды идут на войну, не зная о том, что впереди их ждет не слава героев, а инвалидность и смерть…\nКаждый день войны уносит жизни чьих-то отцов, сыновей, а газеты тем временем бесстрастно сообщают: «На Западном фронте без перемен»…\nЭта книга – не обвинение, не исповедь."),
#                   Book(book="Triumphal Arch", icon_book="static/img/triumphal_arch.jpg",
#                       description="\"Триумфальная арка\" – пронзительная история любви всему наперекор, любви, приносящей боль, но и дарующей бесконечную радость.\nМесто действия – Париж накануне Второй мировой войны. Герой – беженец из Германии, без документов, скрывающийся и от французов, и от нацистов, хирург, спасающий человеческие жизни. Героиня – итальянская актриса, окруженная поклонниками, вспыльчивая, как все артисты, прекрасная и неотразимая.\nИ время, когда влюбленным довелось встретиться, и город, пронизанный ощущением надвигающейся катастрофы, становятся героями этого романа.\n\"Триумфальная арка\" была дважды экранизирована и по-прежнему покоряет читателей всего мира."),
#                   Book(book="Three Comrades", icon_book="static/img/three_comrades.jpg",
#                       description="Книга \"Три товарища\" повествует о жизни троих лучших друзей, которые имеют свою собственную автомастерскую и вней зарабатывают на свою жизнь. Книга полна юмора и в тоже время трагизма. Один из друзей влюбляется, но девушка оказывается больной, причём больной смертельно. У неё туберкулёз. Друзья поддерживают всячески друг друга.")]


# books = remarque.to_dict(only=('name', 'photo', 'books.book', 'books.icon_book', 'books.description'))
# with open('data.json', 'w') as outfile:
#     json.dump(books, outfile)


# session.add_all([remarque])


# session.commit()


class BookResource(Resource):
    def get(self, book_id):
        abort_if_book_not_found(book_id)
        book = session.query(Book).get(book_id)
        return jsonify(
                book.to_dict(only=('id', 'book'))
        )

    def delete(self, book_id):
        abort_if_book_not_found(book_id)
        book = session.query(Book).get(book_id)
        session.delete(book)
        session.commit()
        return jsonify({'success': 'OK'})


@app.route('/api/books')
def get_books():
    query = session.query(Book, Author)
    query = query.join(Author, Book.author_id == Author.id)
    query_all = query.all()
    query_list = []
    for book, authors in query_all:
        books_dic = book.to_dict(only=('id', 'book', 'description', 'icon_book'))
        author_dic = authors.to_dict(only=('name', 'photo'))
        query_dic = books_dic | author_dic
        query_list.append(query_dic)
    return jsonify(
            query_list
    )


@app.route('/api/books', methods=['GET', 'POST'])
def create_book():
    if not request.json:
        return jsonify({'error': 'Empty request'})
    elif not all(key in request.json for key in
                 ['book', 'description', 'icon_book', 'name', 'photo']):
        return jsonify({'error': 'Bad request'})

    author = Author(
        name=request.json['name'],
        photo=request.json['photo']
    )

    book = Book(
        book=request.json['book'],
        description=request.json['description'],
        icon_book=request.json['icon_book']
    )

    session.add(author)
    session.add(book)
    session.commit()
    return jsonify({'success': 'OK'})


api.add_resource(BookResource, '/api/books/<int:book_id>')
app.run(debug=True)
# app.run(port=8080, host='127.0.0.1', debug=True)


