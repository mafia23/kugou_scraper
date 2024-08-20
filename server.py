from flask import Flask, send_file, abort, request
import pymysql
import os

# Flask app setup
app = Flask(__name__)

# Database connection setup
db = pymysql.connect(
    host="localhost",
    user="root",
    password="root",
    port=3306,
    database='lyrics',
    charset='utf8'
)
cursor = db.cursor()
table = 'web_singer'

@app.route('/covers', methods=['GET'])
def get_cover():
    artist = request.args.get('artist')
    if not artist:
        abort(400, description="Artist parameter is required")

    query = "SELECT singerImages FROM {} WHERE singername = %s".format(table)
    cursor.execute(query, (artist,))
    result = cursor.fetchone()

    if result and result[0]:
        file_path = "img/"+result[0]
        if os.path.exists(file_path):
            return send_file(file_path, mimetype='image/jpeg')
        else:
            abort(404, description="Image file not found")
    else:
        abort(404, description="No image found for the given artist")

if __name__ == '__main__':
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
