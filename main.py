from functools import wraps
from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from webforms.forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from drivers.mail import Mail

app = Flask(__name__)
app.secret_key = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Mail Server config
mailing_srv = Mail()


# CONFIGURE USER TABLE
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    name = db.Column(db.String(250), nullable=False)

    # One-to-many relationship with BlogPost
    posts = relationship("BlogPost", back_populates="author")

    # One-to-many relationship with Comments
    comments = relationship("Comment", back_populates='comment_author')


# CONFIGURE TABLE
class BlogPost(db.Model):
    __tablename__ = "blog_post"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    # Many-to-one relationship with User
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object
    author = relationship("User", back_populates="posts")
    # Many-to-one relationship with User
    comments = relationship("Comment", back_populates='post')


# COMMENTS TABLE
class Comment(db.Model):
    __tablename__ = 'comments'
    # Form fields
    id = db.Column(db.Integer, primary_key=True)
    comment_text = db.Column(db.Text, nullable=False)

    # post id for identification of post
    post_id = db.Column(db.Integer, db.ForeignKey("blog_post.id"))

    # "users.id" The users refers to the tablename of the Users class.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    # Post relationship for comments
    post = relationship('BlogPost', back_populates="comments")

    # "comments" refers to the comments property in the User class.
    comment_author = relationship("User", back_populates="comments")


# # Configure db to create a new database
with app.app_context():
    db.create_all()

# CONFIGURE LOGIN MANAGER
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# GRAVATAR
gravatar = Gravatar(
    app,
    size=100,
    rating='g',
    default='retro',
    force_default=False,
    force_lower=False,
    use_ssl=False,
    base_url=None
)


# Admin-only decorator
def author_only(function):
    @wraps(function)
    def admin_decorated_function(*args, **kwargs):
        post = BlogPost.query.get(kwargs.get('post_id'))
        # If id is not 1 then return abort with 403 error
        if current_user.id != post.author_id or current_user.is_authenticated is not True:
            return abort(403)
        # Otherwise continue with the route function
        else:
            return function(*args, **kwargs)

    return admin_decorated_function


# Homepage with all the posts
@app.route('/')
def get_all_posts():
    # All post retrieved
    posts = BlogPost.query.all()

    return render_template("index.html", all_posts=posts, is_logged=current_user.is_authenticated)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form: RegisterForm = RegisterForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            # Get the user by email
            email = form.email.data

            # Check if user already exists
            if User.query.filter_by(email=email).first():
                flash(u"You've already signed up with that email, log in instead!", "warning")
                return redirect(url_for('login'))
            else:
                # Create a new user
                new_user = User(
                    email=email,
                    password=generate_password_hash(form.password.data, method='pbkdf2:sha256', salt_length=8),
                    name=form.name.data
                )

                # Add new user to database
                db.session.add(new_user)
                db.session.commit()

                # Log in the user
                login_user(new_user)

                return redirect(url_for('get_all_posts'))

    return render_template("register.html", form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form: LoginForm = LoginForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            # Get the user by email
            user = User.query.filter_by(email=form.email.data).first()

            # Check if user exists
            if user:
                # Check if password is correct
                if check_password_hash(user.password, form.password.data):
                    # Log in the user
                    login_user(user)
                    return redirect(url_for('get_all_posts'))
                else:
                    # Password incorrect
                    flash(u"Password incorrect, please try again.", "danger")
                    return redirect(url_for('login'))
            else:
                # User does not exist
                flash(u"That email does not exist, please register first.", "danger")
                return redirect(url_for('register'))

    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    # Log out the user
    logout_user()
    return redirect(url_for('get_all_posts'))


# Get a post by post id
@app.route("/post/<int:index>", methods=['GET', 'POST'])
def show_post(index):
    # Comment form
    comment_form = CommentForm()
    # post retrieved by the index
    requested_post = BlogPost.query.get(index)

    # Author only access
    is_author = False if current_user.is_anonymous else current_user.id == requested_post.author_id

    # comments on the post
    comments = Comment.query.filter_by(post_id=requested_post.id, author_id=requested_post.author_id)

    if request.method == 'POST':
        if comment_form.validate_on_submit():
            if current_user.is_authenticated:
                new_comment = Comment(
                    comment_text=comment_form.comment.data,
                    author_id=current_user.id,
                    post_id=requested_post.id,
                )

                db.session.add(new_comment)
                db.session.commit()

                return redirect(url_for('show_post', index=index))
            else:
                return redirect(url_for('login'))

    return render_template(
        "post.html",
        post=requested_post,
        comment_form=comment_form,
        comments=comments,
        profile=gravatar,
        author=is_author,
        is_logged=current_user.is_authenticated
    )


# Create a new post
@app.route('/new-post', methods=['GET', 'POST'])
@login_required
def add_new_post():
    # Create a new post
    form = CreatePostForm()

    # Check if the form is valid
    if request.method == 'POST':
        if form.validate_on_submit():
            # Create a new post
            new_post = BlogPost(
                title=form.title.data,
                subtitle=form.subtitle.data,
                body=form.body.data,
                author_id=current_user.id,
                img_url=form.img_url.data,
                date=date.today().strftime("%B %d, %Y"),
            )

            # Add new post to database
            db.session.add(new_post)
            db.session.commit()

            return redirect(url_for('get_all_posts'))

    return render_template("make-post.html", form=form, action="New Post")


# Edit a post
@app.route('/edit-post/<int:post_id>', methods=['GET', 'POST'])
@login_required
@author_only
def edit_post(post_id):
    # Get the post by id
    requested_post = BlogPost.query.get(post_id)

    # Create a form and populate it with the post data
    edit_form = CreatePostForm(
        title=requested_post.title,
        subtitle=requested_post.subtitle,
        author=requested_post.author,
        img_url=requested_post.img_url,
        body=requested_post.body
    )

    # Check if the form is valid
    if request.method == 'POST':
        if edit_form.validate_on_submit():
            # Update the post data
            requested_post.title = edit_form.title.data
            requested_post.subtitle = edit_form.subtitle.data
            requested_post.body = edit_form.body.data
            requested_post.img_url = edit_form.img_url.data

            # Commit the changes to the database
            db.session.commit()

            return redirect(url_for('show_post', index=post_id))

    return render_template(
        "make-post.html",
        action="Edit Post",
        form=edit_form
    )


# Delete a post
@app.route('/delete/<int:post_id>')
@login_required
@author_only
def delete_post(post_id):
    # post retrieved by the index
    post_to_delete = BlogPost.query.get(post_id)

    # Delete the post
    db.session.delete(post_to_delete)
    db.session.commit()

    return redirect(url_for('get_all_posts'))


# render About page
@app.route("/about")
def about():
    return render_template("about.html")


# render contact page
@app.route("/contact", methods=['POST', 'GET'])
def contact():
    if request.method == 'POST':
        contact_data = {
            "name": request.form['name'],
            "email": request.form['email'],
            "phone": request.form['phone'],
            "message": request.form['message'],
        }

        try:
            mailing_srv.send_mail(contact_data)
            flash("Email sent successfully!", "success")
        except Exception as e:
            flash("Error sending email: " + str(e), "error")

        return redirect(url_for('contact'))

    return render_template("contact.html")


# Driver Code
if __name__ == "__main__":
    app.run(debug=True, port=5000)
