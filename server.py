from flask import Flask, send_file, abort, request
import sqlite3
import os
import requests

# Flask app setup
app = Flask(__name__)

# SQLite database setup
db_path = 'lyrics.db'


def get_db_connection():
    return sqlite3.connect(db_path)


@app.route('/covers', methods=['GET'])
def get_cover():
    artist = request.args.get('artist')
    if not artist:
        abort(400, description="Artist parameter is required")

    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT img_url FROM web_singer WHERE singername = ?"
    cursor.execute(query, (artist,))
    result = cursor.fetchone()
    conn.close()

    if result and result[0]:
        img_url = result[0]
        if img_url:
            try:
                response = requests.get(img_url, stream=True)
                if response.status_code == 200:
                    return send_file(
                        response.raw,
                        mimetype=response.headers.get('Content-Type', 'image/jpeg'),
                        as_attachment=False
                    )
                else:
                    abort(404, description="Image not found at the provided URL")
            except Exception as e:
                abort(500, description=f"Error fetching image: {str(e)}")
        else:
            abort(404, description="No image URL found for the given artist")
    else:
        abort(404, description="No image found for the given artist")


if __name__ == '__main__':
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
