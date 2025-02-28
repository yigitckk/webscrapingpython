from flask import Flask, render_template, request
import sqlite3
import json
from datetime import datetime

app = Flask(__name__)


def get_db_connection():
    conn = sqlite3.connect('news_aggregator.db')
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def index():
    conn = get_db_connection()

    # Default filters
    days = int(request.args.get('days', 7))
    category = request.args.get('category', 'all')
    source = request.args.get('source', 'all')
    search = request.args.get('search', '')

    # Build query with filters
    query = '''
    SELECT a.id, a.title, a.url, a.source, a.published_date, a.summary, a.category, GROUP_CONCAT(t.tag, ',') as tags
    FROM articles a
    LEFT JOIN article_tags t ON a.id = t.article_id
    WHERE DATE(a.added_date) >= DATE('now', ? || ' days')
    '''
    params = [f'-{days}']

    if category != 'all':
        query += ' AND a.category = ?'
        params.append(category)

    if source != 'all':
        query += ' AND a.source = ?'
        params.append(source)

    if search:
        query += ' AND (a.title LIKE ? OR a.summary LIKE ?)'
        search_param = f'%{search}%'
        params.append(search_param)
        params.append(search_param)

    query += ' GROUP BY a.id ORDER BY a.added_date DESC LIMIT 100'

    articles = conn.execute(query, params).fetchall()

    # Get available categories and sources for filters
    categories = conn.execute('SELECT DISTINCT category FROM articles').fetchall()
    sources = conn.execute('SELECT DISTINCT source FROM articles').fetchall()

    # Get popular tags
    tags = conn.execute('''
    SELECT tag, COUNT(*) as count 
    FROM article_tags 
    GROUP BY tag 
    ORDER BY count DESC 
    LIMIT 20
    ''').fetchall()

    conn.close()

    return render_template('index.html',
                           articles=articles,
                           categories=categories,
                           sources=sources,
                           tags=tags,
                           selected_days=days,
                           selected_category=category,
                           selected_source=source,
                           search=search)


@app.route('/tags/<tag>')
def tag_view(tag):
    conn = get_db_connection()

    articles = conn.execute('''
    SELECT a.id, a.title, a.url, a.source, a.published_date, a.summary, a.category, GROUP_CONCAT(t2.tag, ',') as tags
    FROM articles a
    JOIN article_tags t ON a.id = t.article_id
    LEFT JOIN article_tags t2 ON a.id = t2.article_id
    WHERE t.tag = ?
    GROUP BY a.id
    ORDER BY a.added_date DESC
    ''', (tag,)).fetchall()

    conn.close()

    return render_template('tag.html', articles=articles, tag=tag)


@app.route('/stats')
def stats():
    conn = get_db_connection()

    # Get daily article counts
    daily_counts = conn.execute('''
    SELECT DATE(added_date) as date, COUNT(*) as count
    FROM articles
    GROUP BY DATE(added_date)
    ORDER BY date DESC
    LIMIT 30
    ''').fetchall()

    # Get source distribution
    sources = conn.execute('''
    SELECT source, COUNT(*) as count
    FROM articles
    GROUP BY source
    ORDER BY count DESC
    ''').fetchall()

    # Get category distribution
    categories = conn.execute('''
    SELECT category, COUNT(*) as count
    FROM articles
    GROUP BY category
    ORDER BY count DESC
    ''').fetchall()

    # Get tag distribution
    tags = conn.execute('''
    SELECT tag, COUNT(*) as count
    FROM article_tags
    GROUP BY tag
    ORDER BY count DESC
    LIMIT 50
    ''').fetchall()

    conn.close()

    return render_template('stats.html',
                           daily_counts=daily_counts,
                           sources=sources,
                           categories=categories,
                           tags=tags)


if __name__ == '__main__':
    app.run(debug=True)