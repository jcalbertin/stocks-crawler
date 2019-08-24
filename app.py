import os

from flask import Flask, jsonify, request, abort
from flask_pymongo import PyMongo
from stocks_spider import StockSpider


# A GoHorse made app

DEBUG = os.getenv('DEBUG', True)
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/stocksCrawler')
CRAWLER_EMAIL = os.getenv('CRAWLER_EMAIL')
CRAWLER_PASSWORD = os.getenv('CRAWLER_PASSWORD')

app = Flask(__name__)
app.config['MONGO_URI'] = MONGODB_URI

mongo = PyMongo(app)
db = mongo.db
stocks_collection = db.stocks
stocks_analysis_collection = db.fundamentalistAnalysis

uri_data = MONGODB_URI.rsplit('/', 1)
db_name = uri_data[-1]
mongo_url = ''.join(uri_data[:-1])
SPIDER = StockSpider(
    CRAWLER_EMAIL, CRAWLER_PASSWORD, mongo_url=mongo_url, db_name=db_name,
)


def convert_id(document):
    document['_id'] = str(document['_id'])
    return document


@app.route('/')
def index():
    return jsonify({
        'stocks': f'{request.url}stocks/',
    })


@app.route('/stocks/', methods=['GET', 'POST'])
def stocks_list():
    if request.method != 'POST':
        stocks = [stock for stock in stocks_collection.find()]
    else:
        if not CRAWLER_EMAIL or not CRAWLER_PASSWORD:
            return jsonify({
                'error': True,
                'message': 'Credentials not set',
            })
        stocks = SPIDER.parse_stocks(save=True)
    return jsonify([convert_id(stock) for stock in stocks])


@app.route('/stocks/analysis/')
def analysis_list():
    return jsonify([convert_id(a) for a in stocks_analysis_collection.find()])


@app.route('/stocks/<string:stock_code>/analysis')
def analysis_detail(stock_code):
    code = stock_code.upper()
    analysis = stocks_analysis_collection.find_one({
        'code': code,
    })
    if not analysis:
        stock = stocks_collection.find_one({'code': code})
        if not stock:
            return abort(404)
        analysis = SPIDER.extract_all_fundamentalist_data(code, save=True)
    return jsonify(convert_id(analysis))


@app.route('/stocks/<string:stock_code>/')
def stocks_detail(stock_code):
    code = stock_code.upper()
    stock = stocks_collection.find_one({'code': code})
    if not stock:
        return abort(404)
    return jsonify(convert_id(stock))


if __name__ == '__main__':
    app.run(debug=DEBUG)