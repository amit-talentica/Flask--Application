from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
#from data import Quotes
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps


app=Flask(__name__)

# Config MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'akm'
app.config['MYSQL_DB'] = 'myflaskapp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
# init MYSQL
mysql = MySQL(app)

#Quotes=Quotes()

#index
@app.route('/')
def index():
    return render_template('home.html')
    #about
@app.route('/about')
def about():
    return render_template('about.html')
#quotes
@app.route('/quotes')
def quotes():
     # Create cursor
    cur = mysql.connection.cursor()

    # Get articles
    result = cur.execute("SELECT * FROM quotes")

    quotes = cur.fetchall()

    if result > 0:
        return render_template('quotes.html', quotes=quotes)
    else:
        msg = 'No Quotes Found'
        return render_template('quotes.html', msg=msg)
    # Close connection
    cur.close()
#single article
@app.route('/quote/<string:id>/')
def quote(id):
    cur=mysql.connection.cursor()
    result=cur.execute("SELECT * FROM quotes WHERE id= %s",[id])
    quote=cur.fetchone()
    return render_template('quote.html',quote=quote)

#RegisterForm
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')

# User Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        # Create cursor
        cur = mysql.connection.cursor()

        # Execute query
        cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))

        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash('You are now registered and can log in', 'success')

        return redirect(url_for('index'))
    return render_template('register.html', form=form)

# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get Form Fields
        username = request.form['username']
        password_candidate = request.form['password']

        # Create cursor
        cur = mysql.connection.cursor()

        # Get user by username
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            # Get stored hash
            data = cur.fetchone()
            password = data['password']

            # Compare Passwords
            if sha256_crypt.verify(password_candidate, password):
                # Passed
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)
            # Close connection
            cur.close()
        else:
            error = 'Username not found'
            return render_template('login.html', error=error)

    return render_template('login.html')

# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap


#Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out','success')
    return redirect(url_for('login'))


#dashboard

@app.route('/dashboard')
@is_logged_in
def dashboard():
    print("Here 1")
     # Create cursor
    cur = mysql.connection.cursor()

    # Get articles
    #result = cur.execute("SELECT * FROM articles")
    # Show articles only from the user logged in
    result = cur.execute("SELECT * FROM quotes WHERE author = %s", [session['username']])

    quotes = cur.fetchall()

    print("Here 2", quotes)
    print("Here 3", result)

    if result > 0:
        print("Here in result")
        return render_template('dashboard.html',quotes=quotes)
    else:
        msg = 'No Quotes Found'
        return render_template('dashboard.html', msg=msg)
    # Close connection
    cur.close()

# Quote Form Class
class QuoteForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=200)])
    body = TextAreaField('Body', [validators.Length(min=20)])
# Add Quote
@app.route('/add_quote', methods=['GET', 'POST'])
@is_logged_in
def add_quote():
    form = QuoteForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        # Create Cursor
        cur = mysql.connection.cursor()

        # Execute
        cur.execute("INSERT INTO quotes(title, body, author) VALUES(%s, %s, %s)",(title, body, session['username']))

        # Commit to DB
        mysql.connection.commit()

        #Close connection
        cur.close()

        flash('Quote Created', 'success')

        return redirect(url_for('dashboard'))

    return render_template('add_quote.html', form=form)


##Edit Quotes
@app.route('/edit_quote/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_quote(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Get article by id
    result = cur.execute("SELECT * FROM quotes WHERE id = %s", [id])

    quote = cur.fetchone()
    cur.close()
    # Get form
    form = QuoteForm(request.form)

    # Populate article form fields
    form.title.data = quote['title']
    form.body.data = quote['body']

    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']

        # Create Cursor
        cur = mysql.connection.cursor()
        app.logger.info(title)
        # Execute
        cur.execute ("UPDATE quotes SET title=%s, body=%s WHERE id=%s",(title, body, id))
        # Commit to DB
        mysql.connection.commit()

        #Close connection
        cur.close()

        flash('Quote Updated', 'success')

        return redirect(url_for('dashboard'))

    return render_template('edit_quote.html', form=form)

# Delete Quote
@app.route('/delete_quote/<string:id>', methods=['POST'])
@is_logged_in
def delete_quote(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Execute
    cur.execute("DELETE FROM quotes WHERE id = %s", [id])

    # Commit to DB
    mysql.connection.commit()

    #Close connection
    cur.close()

    flash('Quote Deleted', 'success')

    return redirect(url_for('dashboard'))











if __name__ == '__main__' :
    app.secret_key='secret123'
    app.run(debug=True)
