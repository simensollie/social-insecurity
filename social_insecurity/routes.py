"""Provides all routes for the Social Insecurity application.

This file contains the routes for the application. It is imported by the social_insecurity package.
It also contains the SQL queries used for communicating with the database.
"""

from pathlib import Path

from flask import current_app as app
from flask import flash, redirect, render_template, send_from_directory, url_for
from flask_login import login_user, logout_user, login_required, current_user
from markupsafe import escape

from social_insecurity import sqlite
from social_insecurity.forms import CommentsForm, FriendsForm, IndexForm, PostForm, ProfileForm
from social_insecurity.models import User

@app.route("/", methods=["GET", "POST"])
@app.route("/index", methods=["GET", "POST"])
def index():
    """Provides the index page for the application.

    It reads the composite IndexForm and based on which form was submitted,
    it either logs the user in or registers a new user.

    If no form was submitted, it simply renders the index page.
    """
    index_form = IndexForm()
    login_form = index_form.login
    register_form = index_form.register

    if login_form.is_submitted() and login_form.submit.data:
        get_user = """
            SELECT *
            FROM Users
            WHERE username = ?;
            """
        user = sqlite.query(get_user, login_form.username.data, one=True)

        if user is None:
            flash("Sorry, username or password is not correct.", category="warning")
        elif user["password"] != login_form.password.data:
            flash("Sorry, username or password is not correct.", category="warning")
        else:
            # Create User object and log them in
            user_obj = User(
                user['id'],
                user['username'],
                user['first_name'],
                user['last_name'],
                user['password']
            )
            login_user(user_obj, remember=login_form.remember_me.data)
            flash("Login successful!", category="success")
            return redirect(url_for("stream", username=user['username']))

    elif register_form.is_submitted() and register_form.submit.data:
        insert_user = """
            INSERT INTO Users (username, first_name, last_name, password)
            VALUES (?, ?, ?, ?);
            """
        sqlite.query(insert_user, register_form.username.data, register_form.first_name.data, register_form.last_name.data, register_form.password.data)
        flash("User successfully created!", category="success")
        return redirect(url_for("index"))

    return render_template("index.html.j2", title="Welcome", form=index_form)

@app.route("/logout")
@login_required
def logout():
    """Log out the current user."""
    logout_user()
    flash("You have been logged out.", category="success")
    return redirect(url_for("index"))

@app.route("/stream/<string:username>", methods=["GET", "POST"])
@login_required
def stream(username: str):
    """
    Provides the stream page for the application.

    If a form was submitted, it reads the form data and inserts a new post into the database.

    Otherwise, it reads the username from the URL and displays all posts from the user and their friends.
    """
    # CRITICAL: Verify authenticated user matches requested username (fixes IDOR vulnerability)
    if current_user.username != username:
        flash("You don't have permission to access this page.", category="error")
        return redirect(url_for("stream", username=current_user.username))

    post_form = PostForm()

    if post_form.is_submitted():
        if post_form.image.data:
            path = Path(app.instance_path) / app.config["UPLOADS_FOLDER_PATH"] / post_form.image.data.filename
            post_form.image.data.save(path)

        insert_post = """
            INSERT INTO Posts (u_id, content, image, creation_time)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP);
            """
        image_filename = post_form.image.data.filename if post_form.image.data else None
        # Sanitize user input to prevent XSS
        sanitized_content = escape(post_form.content.data) if post_form.content.data else None
        # Use current_user.id instead of querying user again
        sqlite.query(insert_post, current_user.id, sanitized_content, image_filename)
        return redirect(url_for("stream", username=username))

    get_posts = """
         SELECT p.*, u.*, (SELECT COUNT(*) FROM Comments WHERE p_id = p.id) AS cc
         FROM Posts AS p JOIN Users AS u ON u.id = p.u_id
         WHERE p.u_id IN (SELECT u_id FROM Friends WHERE f_id = ?) OR p.u_id IN (SELECT f_id FROM Friends WHERE u_id = ?) OR p.u_id = ?
         ORDER BY p.creation_time DESC;
        """
    # Use current_user.id instead of querying user again
    posts = sqlite.query(get_posts, current_user.id, current_user.id, current_user.id)
    return render_template("stream.html.j2", title="Stream", username=username, form=post_form, posts=posts)


@app.route("/comments/<string:username>/<int:post_id>", methods=["GET", "POST"])
@login_required
def comments(username: str, post_id: int):
    """Provides the comments page for the application.

    If a form was submitted, it reads the form data and inserts a new comment into the database.

    Otherwise, it reads the username and post id from the URL and displays all comments for the post.
    """
    # CRITICAL: Verify authenticated user matches requested username (fixes IDOR vulnerability)
    if current_user.username != username:
        flash("You don't have permission to access this page.", category="error")
        return redirect(url_for("stream", username=current_user.username))

    comments_form = CommentsForm()

    if comments_form.is_submitted():
        insert_comment = """
            INSERT INTO Comments (p_id, u_id, comment, creation_time)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP);
            """
        # Sanitize user input to prevent XSS
        sanitized_comment = escape(comments_form.comment.data) if comments_form.comment.data else None
        # Use current_user.id instead of querying user again
        sqlite.query(insert_comment, post_id, current_user.id, sanitized_comment)

    get_post = """
        SELECT *
        FROM Posts AS p JOIN Users AS u ON p.u_id = u.id
        WHERE p.id = ?;
        """
    get_comments = """
        SELECT DISTINCT *
        FROM Comments AS c JOIN Users AS u ON c.u_id = u.id
        WHERE c.p_id = ?
        ORDER BY c.creation_time DESC;
        """
    post = sqlite.query(get_post, post_id, one=True)
    comments = sqlite.query(get_comments, post_id)
    return render_template(
        "comments.html.j2", title="Comments", username=username, form=comments_form, post=post, comments=comments
    )


@app.route("/friends/<string:username>", methods=["GET", "POST"])
@login_required
def friends(username: str):
    """Provides the friends page for the application.

    If a form was submitted, it reads the form data and inserts a new friend into the database.

    Otherwise, it reads the username from the URL and displays all friends of the user.
    """
    # CRITICAL: Verify authenticated user matches requested username (fixes IDOR vulnerability)
    if current_user.username != username:
        flash("You can only view your own friends list.", category="error")
        return redirect(url_for("friends", username=current_user.username))

    friends_form = FriendsForm()

    if friends_form.is_submitted():
        get_friend = """
            SELECT *
            FROM Users
            WHERE username = ?;
            """
        friend = sqlite.query(get_friend, friends_form.username.data, one=True)
        get_friends = """
            SELECT f_id
            FROM Friends
            WHERE u_id = ?;
            """
        # Use current_user.id instead of querying user again
        existing_friends = sqlite.query(get_friends, current_user.id)

        if friend is None:
            flash("User does not exist!", category="warning")
        elif friend["id"] == current_user.id:
            flash("You cannot be friends with yourself!", category="warning")
        elif friend["id"] in [f["f_id"] for f in existing_friends]:
            flash("You are already friends with this user!", category="warning")
        else:
            insert_friend = """
                INSERT INTO Friends (u_id, f_id)
                VALUES (?, ?);
                """
            # Use current_user.id instead of querying user again
            sqlite.query(insert_friend, current_user.id, friend["id"])
            flash("Friend successfully added!", category="success")

    get_friends = """
        SELECT *
        FROM Friends AS f JOIN Users as u ON f.f_id = u.id
        WHERE f.u_id = ? AND f.f_id != ?;
        """
    # Use current_user.id instead of querying user again
    friends = sqlite.query(get_friends, current_user.id, current_user.id)
    return render_template("friends.html.j2", title="Friends", username=username, friends=friends, form=friends_form)


@app.route("/profile/<string:username>", methods=["GET", "POST"])
@login_required
def profile(username: str):
    """Provides the profile page for the application.

    If a form was submitted, it reads the form data and updates the user's profile in the database.

    Otherwise, it reads the username from the URL and displays the user's profile.
    """
    # CRITICAL: Verify authenticated user matches requested username (fixes IDOR vulnerability)
    if current_user.username != username:
        flash("You can only edit your own profile.", category="error")
        return redirect(url_for("profile", username=current_user.username))

    profile_form = ProfileForm()
    get_user = """
        SELECT *
        FROM Users
        WHERE username = ?;
        """
    user = sqlite.query(get_user, username, one=True)

    if profile_form.is_submitted():
        # CRITICAL: Double-check authorization before allowing update
        if current_user.username != username:
            flash("You can only edit your own profile.", category="error")
            return redirect(url_for("profile", username=current_user.username))

        update_profile = """
            UPDATE Users
            SET education=?, employment=?, music=?, movie=?, nationality=?, birthday=?
            WHERE username=?;
            """
        # Sanitize user input to prevent XSS
        sqlite.query(
            update_profile,
            escape(profile_form.education.data) if profile_form.education.data else None,
            escape(profile_form.employment.data) if profile_form.employment.data else None,
            escape(profile_form.music.data) if profile_form.music.data else None,
            escape(profile_form.movie.data) if profile_form.movie.data else None,
            escape(profile_form.nationality.data) if profile_form.nationality.data else None,
            profile_form.birthday.data, 
            username
        )
        flash("Profile updated successfully!", category="success")
        return redirect(url_for("profile", username=username))

    return render_template("profile.html.j2", title="Profile", username=username, user=user, form=profile_form)


@app.route("/uploads/<string:filename>")
def uploads(filename):
    """Provides an endpoint for serving uploaded files."""
    return send_from_directory(Path(app.instance_path) / app.config["UPLOADS_FOLDER_PATH"], filename)
