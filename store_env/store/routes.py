import os
import secrets
from PIL import Image
from flask import Flask, escape, request, render_template, url_for, flash, redirect, abort
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message
from store import db, app, bcrypt, mail
from store.models import User, Sell
from store.forms import RegistrationForm, LoginForm, UpdateAccountForm, SellForm

@app.route("/")
@app.route("/home")
def home():
    page = request.args.get('page', 1, type = int)
    sells = Sell.query.order_by(Sell.date_posted.desc()).paginate(page = page, per_page=5)
    return render_template('home.html', sells=sells)


@app.route("/register", methods=['GET', 'POST'])
def register():
	if current_user.is_authenticated:
		return redirect(url_for('home'))
	form = RegistrationForm()
	if form.validate_on_submit():
		hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
		user = User(username=form.username.data, email=form.email.data, password=hashed_password)
		db.session.add(user)
		db.session.commit()
		flash('Your account has been created! You are now able to log in', 'success')
		return redirect(url_for('login'))
	return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
	if current_user.is_authenticated:
		return redirect(url_for('home'))
	form = LoginForm()
	if form.validate_on_submit():
		user = User.query.filter_by(email=form.email.data).first()
		if user and bcrypt.check_password_hash(user.password, form.password.data):
			login_user(user, remember=form.remember.data)
			next_page = request.args.get('next')
			return redirect(next_page) if next_page else redirect(url_for('home'))
		else:
			flash(f'Loggin Faild, Please check email and password', 'danger')
	return render_template('login.html', title='Login', form=form)


@app.route("/logout")
def logout():
	logout_user()
	return redirect(url_for('home'))


def save_pitcure(form_picture):
	random_hex = secrets.token_hex(8)
	_, f_ext = os.path.splitext(form_picture.filename)
	picture_fn = random_hex + f_ext
	picture_path = os.path.join(app.root_path, 'static/img', picture_fn)

	output_size = (125, 125)
	i = Image.open(form_picture)
	i.thumbnail(output_size)
	i.save(picture_path)

	return picture_fn


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
	form = UpdateAccountForm()
	if form.validate_on_submit():
		if form.picture.data:
			picture_file = save_pitcure(form.picture.data)
			current_user.image_file = picture_file
		current_user.username = form.username.data
		current_user.email = form.email.data
		db.session.commit()
		flash('your account has been updated', 'success')
		return redirect(url_for('account'))
	elif request.method == 'GET':
		form.username.data = current_user.username
		form.email.data = current_user.email
	image_file = url_for('static', filename='img/' + current_user.image_file)
	return render_template('account.html', title='Account', image_file=image_file, form=form)


@app.route("/sell/new", methods=['GET', 'POST'])
@login_required
def new_sell():
	form = SellForm()
	if form.picture.data:
			picture_file = save_pitcure(form.picture.data)
	if form.validate_on_submit():
		sell = Sell(title=form.title.data, content=form.content.data, author=current_user,
					price=form.price.data, picture_file=picture_file)
		db.session.add(sell)
		db.session.commit()
		flash('Your new sell has been created!', 'success')
		return redirect(url_for('home'))
	return render_template('create_sell.html', title='New Sell', form=form, legend='New Sell')


@app.route("/sell/<int:sell_id>")
def sell(sell_id):
	sell = Sell.query.get_or_404(sell_id)
	return render_template('sell.html', title=sell.title, sell=sell)
    
@app.route("/sell/<int:sell_id>/update", methods=['GET', 'POST'])
@login_required
def update_sell(sell_id):
	sell = Sell.query.get_or_404(sell_id)
	if sell.author != current_user:
		abort(403)
	form = SellForm()
	if form.validate_on_submit():
		sell.title = form.title.data
		sell.content = form.content.data
		db.session.commit()
		flash('Your sell has been updated!', 'success')
		return redirect(url_for('sell', sell_id=sell.id))
		
	elif request.method == 'GET':
		form.title.data = sell.title
		form.content.data = sell.content
	return render_template('create_sell.html', title='Update sell', form=form, legend='Update sell')
    

@app.route("/sell/<int:sell_id>/delete", methods=['POST'])
@login_required
def delete_sell(sell_id):
	sell = Sell.query.get_or_404(sell_id)
	if sell.author != current_user:
		abort(403)
	db.session.delete(sell)
	db.session.commit()
	flash('Your sell has been deleted!')
	return redirect(url_for('home'))

@app.route("/user/<string:username>")
def user_sells(username):
	page = request.args.get('page', 1, type=int)
	user = User.query.filter_by(username = username).first_or_404()
	sells = Sell.query.filter_by(author = user).order_by(Sell.date_posted.desc()).paginate(page=page, per_page=5)
	return render_template('user_sell.html', sells=sells, user=user)