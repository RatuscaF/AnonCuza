import eventlet  # First import
eventlet.monkey_patch()  # Monkey patching must be done right after importing eventlet


from flask import Flask, flash, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy; # Database
from datetime import datetime
from flask_socketio import SocketIO, send, emit
from datetime import datetime, timezone, timedelta

EET = timezone(timedelta(hours=2))  # Standard time (UTC +2)
EEST = timezone(timedelta(hours=3))  # Daylight saving time (UTC +3)

# Get the current time in Eastern European Time (EET)
current_time_eet = datetime.now(EET)  # Use UTC+2 for standard time
print("Current time in EET:", current_time_eet)

# Get the current time in Eastern European Summer Time (EEST)
current_time_eest = datetime.now(EEST)  # Use UTC+3 for daylight saving time
print("Current time in EEST:", current_time_eest)

app = Flask(__name__)

# Configure databases
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)
socketio = SocketIO(app)  # Initialize SocketIO


#Models
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(), nullable=False)
    date_created = db.Column(db.DateTime, default=lambda: datetime.now(EET))  # Set timezone to EET (UTC+2)
    comments = db.relationship('Comment', backref='post', lazy=True)

    def __repr__(self):
        return '<Task %r>' % self.id

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)
    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]), lazy=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(EET))  # Set timezone to EET (UTC+2)


# Routes
@app.route('/')
@app.route('/index')
def index():
    posts = Post.query.order_by(Post.date_created.desc()).all()
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


# Custom filter to replace newlines with <br> tags
def nl2br(value):
    return value.replace("\n", "<br>")

# Register the custom filter
app.jinja_env.filters['nl2br'] = nl2br



@app.route('/post/<int:id>')
def view_post(id):
    post = Post.query.get_or_404(id)
    comments = Comment.query.filter_by(post_id=id, parent_id=None).all()
    return render_template('view_post.html', post=post, comments=comments)

@app.context_processor
def inject_current_path():
    # Pass `path` and `endpoint` to all templates
    return {
        'current_path': request.path,
        'current_endpoint': request.endpoint
    }

@app.route('/comment/<int:post_id>', methods=['POST'])
def create_comment(post_id):
    content = request.form['content']
    parent_id = request.form.get('parent_id')  # Get parent_id if it's a reply
    
    if not content:
        return "Comment content is required!", 400
    
    new_comment = Comment(content=content, post_id=post_id, parent_id=parent_id)
    db.session.add(new_comment)
    db.session.commit()
    return redirect(url_for('view_post', id=post_id))

@app.route('/chat')
def chat():
    messages = Message.query.order_by(Message.timestamp.asc()).all()  # Load all messages
    return render_template('chat.html', messages=messages)

# SocketIO Events
@socketio.on('send_message')
def handle_message(data):
    message_content = data.get('message')
    if message_content and len(message_content.strip()) > 0:
        # Save message to the database
        new_message = Message(content=message_content)
        db.session.add(new_message)
        db.session.commit()

        # Broadcast message to all clients
        emit('message', {
            'message': message_content,
            'timestamp': new_message.timestamp.strftime('%H:%M')
        }, broadcast=True)



#Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


if __name__ == "__main__":

    with app.app_context():
        db.create_all()

    #app.run(host='0.0.0.0', port=5000, debug=True)

    socketio.run(app, host='0.0.0.0', port=5000, debug=False)