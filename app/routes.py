import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.utils import secure_filename
from app import db
from app.models import User, Quiz, Question, Choice
from app.forms import LoginForm, RegistrationForm, UploadForm
from app.utils.pdf_parser import extract_text_from_pdf
from app.utils.question_generator import generate_questions_from_text # Using the Gemini-powered function

bp = Blueprint('main', __name__)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@bp.route('/')
@bp.route('/index')
@login_required
def index():
    quizzes = Quiz.query.filter_by(user_id=current_user.id).order_by(Quiz.timestamp.desc()).all()
    return render_template('index.html', title='Home', quizzes=quizzes)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('main.login'))
        login_user(user, remember=form.remember_me.data)
        return redirect(url_for('main.index'))
    return render_template('login.html', title='Sign In', form=form)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('main.login'))
    return render_template('register.html', title='Register', form=form)

@bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_file():
    form = UploadForm()
    if form.validate_on_submit():
        if 'pdf_file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        file = request.files['pdf_file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            flash('File successfully uploaded, generating quiz...')

            # 1. Extract text from PDF
            pdf_text = extract_text_from_pdf(file_path)
            if not pdf_text:
                flash('Could not extract text from PDF. Please try another file.')
                os.remove(file_path) # Clean up uploaded file
                return redirect(url_for('main.upload_file'))
            
            # 2. Generate questions using Gemini API
            # You can adjust num_questions, e.g., allow user to specify
            generated_questions_data = generate_questions_from_text(pdf_text, num_questions=5)

            if not generated_questions_data:
                flash('Could not generate questions from the text. The content might be too short or complex for the AI, or there was an API error.')
                os.remove(file_path) # Clean up uploaded file
                return redirect(url_for('main.upload_file'))

            # 3. Save quiz to database
            quiz_title = form.quiz_title.data if form.quiz_title.data else f"Quiz from {filename}"
            new_quiz = Quiz(title=quiz_title, author=current_user)
            db.session.add(new_quiz)
            db.session.commit() # Commit to get quiz.id

            for q_data in generated_questions_data:
                question = Question(text=q_data['question_text'], quiz=new_quiz)
                db.session.add(question)
                db.session.commit() # Commit to get question.id

                for c_data in q_data['choices']:
                    choice = Choice(text=c_data['text'], is_correct=c_data['is_correct'], question=question)
                    db.session.add(choice)
                db.session.commit() # Commit choices for this question

            flash(f'Quiz "{new_quiz.title}" generated successfully!')
            # Clean up the PDF after processing if you don't need to store it
            # os.remove(file_path)
            return redirect(url_for('main.view_quiz', quiz_id=new_quiz.id))
        else:
            flash('Invalid file type. Only PDFs are allowed.')
    
    return render_template('upload.html', title='Upload PDF', form=form)


@bp.route('/quiz/<int:quiz_id>')
@login_required
def view_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.user_id != current_user.id:
        flash("You are not authorized to view this quiz.")
        return redirect(url_for('main.index'))
    
    # Eager load questions and choices for efficiency
    questions = Question.query.filter_by(quiz_id=quiz.id).options(db.joinedload(Question.choices)).all()
    
    return render_template('quiz.html', title=quiz.title, quiz=quiz, questions=questions)


@bp.route('/submit_quiz/<int:quiz_id>', methods=['POST'])
@login_required
def submit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.user_id != current_user.id:
        flash("You are not authorized to submit this quiz.")
        return redirect(url_for('main.index'))

    score = 0
    total_questions = 0
    results = []

    questions = Question.query.filter_by(quiz_id=quiz.id).options(db.joinedload(Question.choices)).all()
    
    for question in questions:
        total_questions += 1
        submitted_choice_id = request.form.get(f'question_{question.id}')
        
        is_correct = False
        correct_answer_text = "N/A"
        
        for choice in question.choices:
            if choice.is_correct:
                correct_answer_text = choice.text
            if str(choice.id) == submitted_choice_id and choice.is_correct:
                score += 1
                is_correct = True
        
        results.append({
            'question_text': question.text,
            'submitted_choice_id': submitted_choice_id,
            'is_correct': is_correct,
            'correct_answer': correct_answer_text,
            'all_choices': [{'text': c.text, 'id': c.id, 'is_correct_option': c.is_correct} for c in question.choices]
        })
    
    return render_template('result.html', title='Quiz Result', quiz=quiz, score=score, 
                           total_questions=total_questions, results=results)