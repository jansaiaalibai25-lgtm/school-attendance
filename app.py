from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_school_project' # Нужно для работы входа

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('db.sqlite')
    c = conn.cursor()
    # Создаем таблицы
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, login TEXT, password TEXT, role TEXT, name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY, name TEXT, class_name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS lessons (id INTEGER PRIMARY KEY, subject TEXT, date TEXT, class_name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (id INTEGER PRIMARY KEY, lesson_id INTEGER, student_id INTEGER, status TEXT)''')
    
    # Добавляем тестовых пользователей, если база пустая
    c.execute('SELECT COUNT(*) FROM users')
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (login, password, role, name) VALUES ('teacher', '123', 'teacher', 'Мария Ивановна')")
        c.execute("INSERT INTO users (login, password, role, name) VALUES ('parent', '123', 'parent', 'Сидоров В.В.')")
        c.execute("INSERT INTO users (login, password, role, name) VALUES ('admin', '123', 'admin', 'Завуч Петрова')")
        
        c.execute("INSERT INTO students (name, class_name) VALUES ('Сидоров Алексей', '5-А')")
        c.execute("INSERT INTO students (name, class_name) VALUES ('Иванова Анна', '5-А')")
        c.execute("INSERT INTO students (name, class_name) VALUES ('Петров Иван', '5-А')")
        
        c.execute("INSERT INTO lessons (subject, date, class_name) VALUES ('Математика', '2023-10-01', '5-А')")
        c.execute("INSERT INTO lessons (subject, date, class_name) VALUES ('Русский язык', '2023-10-02', '5-А')")
        conn.commit()
    conn.close()

# Запускаем создание БД при старте
if not os.path.exists('db.sqlite'):
    init_db()

# --- МАРШРУТЫ (СТРАНИЦЫ) ---

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']
        
        conn = sqlite3.connect('db.sqlite')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE login=? AND password=?", (login, password))
        user = c.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user[0]
            session['role'] = user[3]
            session['name'] = user[4]
            if user[3] == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            elif user[3] == 'parent':
                return redirect(url_for('parent_dashboard'))
            elif user[3] == 'admin':
                return redirect(url_for('admin_dashboard'))
        else:
            return "Неверный логин или пароль. <a href='/login'>Назад</a>"
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- СТРАНИЦЫ УЧИТЕЛЯ ---
@app.route('/teacher')
def teacher_dashboard():
    if session.get('role') != 'teacher': return redirect(url_for('login'))
    conn = sqlite3.connect('db.sqlite')
    c = conn.cursor()
    c.execute("SELECT * FROM lessons")
    lessons = c.fetchall()
    conn.close()
    return render_template('teacher.html', lessons=lessons)

@app.route('/lesson/<int:lesson_id>', methods=['GET', 'POST'])
def mark_attendance(lesson_id):
    if session.get('role') != 'teacher': return redirect(url_for('login'))
    
    conn = sqlite3.connect('db.sqlite')
    c = conn.cursor()
    
    if request.method == 'POST':
        # Сохраняем отметки
        for key, value in request.form.items():
            if key.startswith('student_'):
                student_id = key.split('_')[1]
                # Удаляем старую запись, если есть
                c.execute("DELETE FROM attendance WHERE lesson_id=? AND student_id=?", (lesson_id, student_id))
                c.execute("INSERT INTO attendance (lesson_id, student_id, status) VALUES (?, ?, ?)", (lesson_id, student_id, value))
        conn.commit()
        return redirect(url_for('teacher_dashboard'))
    
    # Показываем список учеников
    c.execute("SELECT * FROM students WHERE class_name = (SELECT class_name FROM lessons WHERE id=?)", (lesson_id,))
    students = c.fetchall()
    
    # Получаем уже сохраненные отметки
    c.execute("SELECT student_id, status FROM attendance WHERE lesson_id=?", (lesson_id,))
    existing = {row[0]: row[1] for row in c.fetchall()}
    conn.close()
    
    return render_template('lesson.html', students=students, lesson_id=lesson_id, existing=existing)

# --- СТРАНИЦА РОДИТЕЛЯ ---
@app.route('/parent')
def parent_dashboard():
    if session.get('role') != 'parent': return redirect(url_for('login'))
    # Для простоты привяжем родителя к первому ученику (Сидоров Алексей)
    student_id = 1 
    
    conn = sqlite3.connect('db.sqlite')
    c = conn.cursor()
    c.execute('''SELECT lessons.date, lessons.subject, attendance.status 
                 FROM attendance 
                 JOIN lessons ON attendance.lesson_id = lessons.id 
                 WHERE attendance.student_id = ?''', (student_id,))
    records = c.fetchall()
    conn.close()
    return render_template('parent.html', records=records)

# --- СТРАНИЦА ЗАВУЧА ---
@app.route('/admin')
def admin_dashboard():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    
    conn = sqlite3.connect('db.sqlite')
    c = conn.cursor()
    # Считаем общую статистику
    c.execute('''SELECT lessons.date, lessons.subject, students.name, attendance.status 
                 FROM attendance 
                 JOIN students ON attendance.student_id = students.id
                 JOIN lessons ON attendance.lesson_id = lessons.id''')
    records = c.fetchall()
    conn.close()
    return render_template('admin.html', records=records)

if __name__ == '__main__':
    app.run(debug=True)
    