from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy; # Database
from datetime import datetime



app = Flask(__name__)

# Configure databases
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)

#Models
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(), nullable=False)
    #date_created = db.Column(db.DateTime, default=datetime.now )

    def __repr__(self):
        return '<Task %r>' % self.id

# Routes
@app.route('/')
@app.route('/index')
def index():
    posts = Post.query.all() #order_by(Post.date_created.desc()).all()
    return render_template('index.html', posts=posts)

@app.route('/create', methods=['GET','POST'])
def create_post():
    if request.method == 'POST':
        content = request.form['content']

        if not content:
            return "Title and Content are required!", 400   

        new_post = Post(content=content)
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template("create_post.html")

@app.route('/delete/<int:id>')
def delete_post(id):
    post_to_delete = Post.query.get_or_404(id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('index'))

@app.context_processor
def inject_current_path():
    # Pass `path` and `endpoint` to all templates
    return {
        'current_path': request.path,
        'current_endpoint': request.endpoint
    }

if __name__ == "__main__":

    with app.app_context():
        db.create_all()

    app.run(host='0.0.0.0', port=5000, debug=True)