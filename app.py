import eventlet  # First import
eventlet.monkey_patch()  # Monkey patching must be done right after importing eventlet

import os
from flask import Flask, flash, render_template, request, redirect, url_for, jsonify, request
from flask_sqlalchemy import SQLAlchemy; # Database
from datetime import datetime, timedelta
from flask_socketio import SocketIO, send, emit
from datetime import datetime, timezone, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from dotenv import load_dotenv


EET = timezone(timedelta(hours=2))  # Standard time (UTC +2)
EEST = timezone(timedelta(hours=3))  # Daylight saving time (UTC +3)

# Get the current time in Eastern European Time (EET)
current_time_eet = datetime.now(EET)  # Use UTC+2 for standard time
print("Current time in EET:", current_time_eet)

# Get the current time in Eastern European Summer Time (EEST)
current_time_eest = datetime.now(EEST)  # Use UTC+3 for daylight saving time
print("Current time in EEST:", current_time_eest)

app = Flask(__name__)
# Use environment variable for security

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ratuscaEfrumoasa')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=364)  # Set session lifetime
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=364)  # Set remember cookie duration

login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Redirect unauthorized users to the login page

# Configure databases
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)
socketio = SocketIO(app)  # Initialize SocketIO
load_dotenv()  # Load environment variables from .env file

#Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    last_post_created = db.Column(db.DateTime, nullable=True)  

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(), nullable=False)
    date_created = db.Column(db.DateTime, default=lambda: datetime.now(EET))  # Set timezone to EET (UTC+2)
    likes = db.Column(db.Integer, default=0)  # Number of likes
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Add this line
    user = db.relationship('User', backref=db.backref('posts', lazy=True))     # Add this line
    comments = db.relationship('Comment', primaryjoin="and_(Comment.post_id==Post.id, Comment.parent_id==None)", backref='post', lazy=True)
    # In your Post class, add this method:
    def get_comment_count(self):
        # Count top-level comments
        top_level_count = len(self.comments)
        # Count replies
        replies_count = sum(len(comment.replies) for comment in self.comments)
        return top_level_count + replies_count


    def __repr__(self):
        return '<Task %r>' % self.id

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

    user = db.relationship('User', backref=db.backref('likes', lazy=True))
    post = db.relationship('Post', backref=db.backref('post_likes', lazy=True))

class CommentLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=False)

    user = db.relationship('User', backref=db.backref('comment_likes', lazy=True))
    comment = db.relationship('Comment', backref=db.backref('likes', lazy=True))

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Ensure user_id is defined
    user = db.relationship('User', backref=db.backref('comments', lazy=True))
    like_count = db.Column(db.Integer, default=0)  # New field for like count
    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]), lazy=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('messages', lazy=True))  # Add relationship
    content = db.Column(db.String(), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(EET))  # Set timezone to EET (UTC+2)

# Helper function for comment numbering
def assign_user_numbers(comments):
    user_numbers = {}
    counter = 1
    for comment in comments:
        if comment.user_id not in user_numbers:
            user_numbers[comment.user_id] = counter
            counter += 1
        comment.user_number = user_numbers[comment.user_id]

        for reply in comment.replies:
            if reply.user_id not in user_numbers:
                user_numbers[reply.user_id] = counter
                counter += 1
            reply.user_number = user_numbers[reply.user_id]
    return user_numbers



# Routes
@app.route('/')
@login_required
def index():
    sort_by = request.args.get('sort_by', 'newest')
    today_start = datetime.now(EET).replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = datetime.now(EET).replace(hour=23, minute=59, second=59, microsecond=999999)

    if sort_by == 'likes':
        posts = Post.query.order_by(Post.likes.desc()).all()
    elif sort_by == 'most_liked_today':
        posts = Post.query.filter(Post.date_created.between(today_start, today_end)).order_by(Post.likes.desc()).all()
    elif sort_by == 'most_liked_all_time':
        posts = Post.query.order_by(Post.likes.desc()).all()
    else:  # Default to sorting by newest
        posts = Post.query.order_by(Post.date_created.desc()).all()
    
    return render_template('index.html', posts=posts, sort_by=sort_by, current_time=datetime.now(EET))



@app.route('/create', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        content = request.form['content']

        if not content:
            return "Content is required!", 400

        # Cooldown period
        cooldown_period = timedelta(seconds=30)
        now = datetime.now()  # Make timezone-naive

        # Check if user needs to wait
        if current_user.last_post_created:
            if now - current_user.last_post_created < cooldown_period:
                remaining_time = cooldown_period - (now - current_user.last_post_created)
                flash(f"Please wait {remaining_time.seconds} seconds before posting again.", "warning")
                return redirect(url_for('create_post'))

        # Update the last post created time
        current_user.last_post_created = now
        db.session.commit()

        # Create the new post
        new_post = Post(content=content, user_id=current_user.id)
        db.session.add(new_post)
        db.session.commit()

        flash("Post created successfully!", "success")
        return redirect(url_for('index'))

    return render_template("create_post.html")


# In app.py, add this route
@app.route('/my_posts')
@login_required
def my_posts():
    posts = Post.query.filter_by(user_id=current_user.id)\
        .order_by(Post.date_created.desc()).all()
    return render_template('my_posts.html', posts=posts)


# Custom filter to replace newlines with <br> tags
def nl2br(value):
    return value.replace("\n", "<br>")

# Register the custom filter
app.jinja_env.filters['nl2br'] = nl2br


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Check if username or email is already taken
        if User.query.filter_by(username=username).first():
            flash("Username already exists. Please choose another one.", "danger")
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash("Email already exists. Please use a different email.", "danger")
            return redirect(url_for('register'))

        # If no conflicts, create the user
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash("Logged in successfully!", "success")
            return redirect(url_for('index'))
        else:
            flash("Invalid email or password", "danger")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "info")
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)


@app.route('/post/<int:id>')
def view_post(id):
    post = Post.query.get_or_404(id)
    top_level_comments = Comment.query.filter_by(post_id=id, parent_id=None).all()
    user_numbers = assign_user_numbers(top_level_comments)
    return render_template('view_post.html', post=post, comments=top_level_comments, user_numbers=user_numbers)

@app.context_processor
def inject_current_path():
    # Pass `path` and `endpoint` to all templates
    return {
        'current_path': request.path,
        'current_endpoint': request.endpoint
    }

@app.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    # Check if the user has already liked the post
    existing_like = Like.query.filter_by(user_id=current_user.id, post_id=post_id).first()

    if existing_like:
        flash("You have already liked this post.", "info")
        return redirect(request.referrer)
    
    # Create a new like for the post
    new_like = Like(user_id=current_user.id, post_id=post_id)
    db.session.add(new_like)
    db.session.commit()
    
    # Increment the like count on the post
    post.likes += 1
    db.session.commit()

    flash("You liked the post!", "success")
    return redirect(request.referrer)

@app.route('/like_comment/<int:comment_id>', methods=['POST'])
@login_required
def like_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)

    # Check if the user already liked the comment
    existing_like = CommentLike.query.filter_by(user_id=current_user.id, comment_id=comment_id).first()

    if existing_like:
        flash("You have already liked this comment.", "info")
        return redirect(request.referrer)

    # Add a new like
    new_like = CommentLike(user_id=current_user.id, comment_id=comment_id)
    db.session.add(new_like)

    # Increment the like count
    comment.like_count += 1
    db.session.commit()

    flash("You liked the comment!", "success")
    return redirect(request.referrer)


@app.route('/comment/<int:post_id>', methods=['POST'])
def create_comment(post_id):
    content = request.form['content']
    parent_id = request.form.get('parent_id')  # Get parent_id if it's a reply
    
    if not content:
        flash("Comment content is required!", "danger")
        return redirect(url_for('view_post', id=post_id))
    
    new_comment = Comment(content=content, post_id=post_id, parent_id=parent_id, user_id=current_user.id)
    db.session.add(new_comment)
    db.session.commit()
    flash("Comment added successfully!", "success")
    return redirect(url_for('view_post', id=post_id))


@app.route('/chat')
@login_required
def chat():
    messages = Message.query.order_by(Message.timestamp.asc()).all()  # Load all messages
    return render_template('chat.html', messages=messages)

@socketio.on('send_message')
def handle_message(data):
    message_content = data.get('message')
    if message_content and len(message_content.strip()) > 0:
        # Save message to the database
        new_message = Message(content=message_content, user_id=current_user.id)
        db.session.add(new_message)
        db.session.commit()

        # Broadcast message to all clients with user info
        emit('message', {
            'message': message_content,
            'timestamp': new_message.timestamp.strftime('%H:%M'),
            'user_id': current_user.id,  # Pass user ID for styling
            'username': current_user.username  # Pass username for display
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
    
    # Remove or comment out this line
    # app.run(host='0.0.0.0', port=5000, debug=True)
    
    # Only use this line with eventlet
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)