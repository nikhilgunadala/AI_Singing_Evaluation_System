import os, json, uuid, sqlite3, tempfile
from datetime import datetime
from functools import wraps
from pathlib import Path

import numpy as np
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, abort
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE = Path(__file__).resolve().parent
UPLOAD_DIR = BASE / 'uploads'
UPLOAD_DIR.mkdir(exist_ok=True)
DB_PATH = BASE / 'vocaliq.db'
ALLOWED = {'wav','mp3','m4a','ogg','webm','flac','aiff'}
MAX_BYTES = 25 * 1024 * 1024
app = Flask(__name__)
app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY','change-this-secret-before-deployment'), MAX_CONTENT_LENGTH=MAX_BYTES)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Sign in to open your studio.'


def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at TEXT NOT NULL)''')
        con.execute('''CREATE TABLE IF NOT EXISTS evaluations (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, title TEXT NOT NULL, created_at TEXT NOT NULL, overall REAL NOT NULL, pitch REAL NOT NULL, rhythm REAL NOT NULL, lyrics REAL, duration REAL, bpm REAL, median_pitch REAL, transcript TEXT, reference_lyrics TEXT, feedback TEXT NOT NULL, chart_data TEXT NOT NULL, reference_score REAL, reference_title TEXT, FOREIGN KEY(user_id) REFERENCES users(id))''')
        # Safe migrations for databases created by earlier project versions.
        cols = {r['name'] for r in con.execute('PRAGMA table_info(evaluations)').fetchall()}
        if 'reference_score' not in cols: con.execute('ALTER TABLE evaluations ADD COLUMN reference_score REAL')
        if 'reference_title' not in cols: con.execute('ALTER TABLE evaluations ADD COLUMN reference_title TEXT')
init_db()

class User(UserMixin):
    def __init__(self, row):
        self.id, self.name, self.email = str(row['id']), row['name'], row['email']
@login_manager.user_loader
def load_user(user_id):
    with db() as con: row = con.execute('SELECT * FROM users WHERE id=?',(user_id,)).fetchone()
    return User(row) if row else None

def allowed_file(name): return '.' in name and name.rsplit('.',1)[1].lower() in ALLOWED

def similarity(a,b):
    import re
    norm=lambda s: re.findall(r"[a-z0-9']+", (s or '').lower())
    aa,bb=norm(a),norm(b)
    if not aa or not bb: return None
    from difflib import SequenceMatcher
    return round(SequenceMatcher(None, aa, bb).ratio()*100,1)

def analyze_audio(path, reference_lyrics='', reference_path=None, reference_title=''):
    try:
        import librosa
    except Exception as e:
        raise RuntimeError('Audio analysis dependencies are not ready. Install requirements.txt and try again.') from e
    y, sr = librosa.load(str(path), sr=22050, mono=True)
    if len(y) < sr * 1.0: raise ValueError('Please provide at least one second of audio.')
    duration = float(len(y)/sr)
    if duration > 180: raise ValueError('Please use a clip shorter than 3 minutes.')
    # YIN estimates a fundamental-frequency contour; voiced frames only are used.
    f0 = librosa.yin(y, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C7'), sr=sr, frame_length=2048, hop_length=256)
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=256)[0]
    voiced = f0[(f0 > 0) & np.isfinite(f0)]
    if len(voiced) < 5: raise ValueError('We could not detect enough stable vocal pitch. Try a clearer recording with less background noise.')
    midi = librosa.hz_to_midi(voiced)
    cents = (midi - np.round(midi)) * 100
    # Stability-based practice metrics, explicitly not reference-melody accuracy.
    pitch_stability = float(np.clip(100 - np.std(cents)*1.35, 0, 100))
    voiced_ratio = float(np.clip(np.mean(rms > max(np.max(rms)*0.045, 0.008))*100, 0, 100))
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    bpm = float(np.asarray(tempo).reshape(-1)[0]) if np.size(tempo) else 0.0
    onset = librosa.onset.onset_strength(y=y, sr=sr)
    rhythm = float(np.clip(100 - (np.std(onset)/(np.mean(onset)+1e-6))*18, 0, 100))
    transcript = ''
    try:
        import whisper
        model_name = os.environ.get('WHISPER_MODEL','tiny')
        model = whisper.load_model(model_name)
        transcript = (model.transcribe(str(path), fp16=False).get('text') or '').strip()
    except Exception:
        transcript = ''
    lyric_score = similarity(transcript, reference_lyrics) if reference_lyrics.strip() and transcript else None
    # If a reference track is supplied, align the two pitch contours with DTW and
    # score the median absolute semitone deviation. This is an approximation, not
    # a source-separated vocal comparison; accompaniment can affect pitch tracking.
    reference_score = None
    reference_midi = []
    if reference_path:
        try:
            yr, srr = librosa.load(str(reference_path), sr=22050, mono=True, duration=180)
            if len(yr) >= srr:
                ref_f0 = librosa.yin(yr, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C7'), sr=srr, frame_length=2048, hop_length=512)
                ref_rms = librosa.feature.rms(y=yr, frame_length=2048, hop_length=512)[0]
                valid = (ref_f0 > 0) & np.isfinite(ref_f0)
                if np.sum(valid) >= 5:
                    ref_midi_all = librosa.hz_to_midi(ref_f0[valid])
                    # Thin both contours to keep DTW fast and avoid huge alignment matrices.
                    singer_seq = midi[::max(1, len(midi)//350)][:350]
                    ref_seq = ref_midi_all[::max(1, len(ref_midi_all)//350)][:350]
                    if len(singer_seq) >= 5 and len(ref_seq) >= 5:
                        from librosa.sequence import dtw
                        D, wp = dtw(X=np.asarray(singer_seq, dtype=float)[None, :], Y=np.asarray(ref_seq, dtype=float)[None, :], metric='euclidean')
                        aligned_diffs = np.abs(np.asarray(singer_seq)[wp[:, 0]] - np.asarray(ref_seq)[wp[:, 1]])
                        semitone_error = float(np.median(aligned_diffs))
                        reference_score = round(float(np.clip(100 * np.exp(-semitone_error / 2.5), 0, 100)), 1)
                        reference_midi = [round(float(x), 1) for x in ref_midi_all[::max(1, len(ref_midi_all)//100)][:100]]
        except Exception:
            reference_score = None
    # Use reference melody score when available; otherwise keep a transparent
    # stability-based score. Re-normalize when lyrics transcription is unavailable.
    if reference_score is not None:
        if lyric_score is None: overall = reference_score*0.55 + rhythm*0.25 + pitch_stability*0.20
        else: overall = reference_score*0.45 + rhythm*0.25 + lyric_score*0.20 + pitch_stability*0.10
    elif lyric_score is None: overall = pitch_stability*0.65 + rhythm*0.35
    else: overall = pitch_stability*0.50 + rhythm*0.25 + lyric_score*0.25
    feedback=[]
    feedback.append('Your pitch contour looks steady.' if pitch_stability >= 75 else 'Practice sustained notes slowly and aim for a relaxed, consistent tone.')
    if reference_path:
        feedback.append(f'Reference melody alignment score: {reference_score:.1f}/100.' if reference_score is not None else 'Reference melody comparison could not be calculated. Try cleaner reference audio with a clear melody.')
        if reference_score is not None and reference_score < 65: feedback.append('Practice in short phrases and compare the note direction against the reference; accompaniment may affect automatic pitch tracking.')
    feedback.append('Timing consistency looks promising.' if rhythm >= 70 else 'Try singing with a metronome or the original backing track to strengthen timing.')
    if reference_lyrics.strip():
        feedback.append('Lyrics were compared with the recognized transcript.' if lyric_score is not None else 'Lyrics comparison was skipped because speech recognition did not return a usable transcript.')
    else: feedback.append('Add reference lyrics next time to enable lyric similarity scoring.')
    chart = {'pitch': [round(float(x),1) for x in midi[::max(1,len(midi)//100)][:120]], 'reference_pitch': reference_midi, 'energy':[round(float(x),4) for x in rms[::max(1,len(rms)//100)][:120]], 'labels':[]}
    return {'overall':round(float(overall),1),'pitch':round(pitch_stability,1),'rhythm':round(rhythm,1),'lyrics':lyric_score,'duration':round(duration,1),'bpm':round(bpm,1),'median_pitch':round(float(np.median(voiced)),1),'transcript':transcript,'feedback':feedback,'chart_data':chart,'reference_score':reference_score,'reference_title':reference_title}

@app.route('/')
def home():
    if current_user.is_authenticated: return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/signup', methods=['GET','POST'])
def signup():
    if current_user.is_authenticated: return redirect(url_for('dashboard'))
    if request.method=='POST':
        name=request.form.get('name','').strip()[:80]; email=request.form.get('email','').strip().lower(); password=request.form.get('password','')
        if not name or '@' not in email or len(password)<8:
            flash('Enter your name, a valid email, and a password with at least 8 characters.','error')
        else:
            try:
                with db() as con: con.execute('INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)',(name,email,generate_password_hash(password),datetime.now().isoformat(timespec='seconds')))
                with db() as con: row=con.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
                login_user(User(row)); return redirect(url_for('dashboard'))
            except sqlite3.IntegrityError: flash('An account with this email already exists. Sign in instead.','error')
    return render_template('auth.html', mode='signup')

@app.route('/login', methods=['GET','POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('dashboard'))
    if request.method=='POST':
        email=request.form.get('email','').strip().lower(); password=request.form.get('password','')
        with db() as con: row=con.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
        if row and check_password_hash(row['password_hash'],password): login_user(User(row)); return redirect(url_for('dashboard'))
        flash('Email or password is incorrect.','error')
    return render_template('auth.html', mode='login')

@app.route('/logout', methods=['POST'])
@login_required
def logout(): logout_user(); return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    with db() as con:
        rows=con.execute('SELECT * FROM evaluations WHERE user_id=? ORDER BY id DESC LIMIT 8',(current_user.id,)).fetchall()
        stats=con.execute('SELECT COUNT(*) n, COALESCE(AVG(overall),0) avg, COALESCE(MAX(overall),0) best FROM evaluations WHERE user_id=?',(current_user.id,)).fetchone()
    return render_template('dashboard.html', rows=rows, stats=stats)

@app.route('/evaluate', methods=['POST'])
@login_required
def evaluate():
    file=request.files.get('audio'); ref_file=request.files.get('reference_audio'); lyrics=request.form.get('lyrics','').strip()[:5000]; title=request.form.get('title','Practice take').strip()[:120] or 'Practice take'
    if not file or not file.filename: flash('Choose an audio file or record a take first.','error'); return redirect(url_for('dashboard'))
    if not allowed_file(file.filename): flash('Unsupported singing audio format. Use WAV, MP3, M4A, OGG, WEBM, FLAC or AIFF.','error'); return redirect(url_for('dashboard'))
    if ref_file and ref_file.filename and not allowed_file(ref_file.filename): flash('Unsupported reference format. Use WAV, MP3, M4A, OGG, WEBM, FLAC or AIFF.','error'); return redirect(url_for('dashboard'))
    ext=file.filename.rsplit('.',1)[1].lower(); filename=f'{uuid.uuid4().hex}.{ext}'; path=UPLOAD_DIR/filename; file.save(path)
    ref_path=None; ref_title=''
    if ref_file and ref_file.filename:
        ref_ext=ref_file.filename.rsplit('.',1)[1].lower(); ref_path=UPLOAD_DIR/f'{uuid.uuid4().hex}.{ref_ext}'; ref_file.save(ref_path); ref_title=secure_filename(ref_file.filename)[:120]
    try:
        result=analyze_audio(path,lyrics,ref_path,ref_title)
        with db() as con:
            cur=con.execute('''INSERT INTO evaluations(user_id,title,created_at,overall,pitch,rhythm,lyrics,duration,bpm,median_pitch,transcript,reference_lyrics,feedback,chart_data,reference_score,reference_title) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (current_user.id,title,datetime.now().isoformat(timespec='seconds'),result['overall'],result['pitch'],result['rhythm'],result['lyrics'],result['duration'],result['bpm'],result['median_pitch'],result['transcript'],lyrics,json.dumps(result['feedback']),json.dumps(result['chart_data']),result['reference_score'],result['reference_title']))
            eid=cur.lastrowid
        return redirect(url_for('result', evaluation_id=eid))
    except (RuntimeError,ValueError) as e:
        flash(str(e),'error'); return redirect(url_for('dashboard'))
    except Exception as e:
        app.logger.exception('Evaluation failed'); flash('Audio analysis failed. Try a WAV file or check the installation guide.','error'); return redirect(url_for('dashboard'))
    finally:
        try: path.unlink(missing_ok=True)
        except Exception: pass
        if ref_path:
            try: ref_path.unlink(missing_ok=True)
            except Exception: pass

@app.route('/result/<int:evaluation_id>')
@login_required
def result(evaluation_id):
    with db() as con: row=con.execute('SELECT * FROM evaluations WHERE id=? AND user_id=?',(evaluation_id,current_user.id)).fetchone()
    if not row: abort(404)
    item=dict(row); item['feedback']=json.loads(item['feedback']); item['chart_data']=json.loads(item['chart_data'])
    return render_template('result.html', item=item)

@app.route('/history')
@login_required
def history():
    with db() as con: rows=con.execute('SELECT * FROM evaluations WHERE user_id=? ORDER BY id DESC',(current_user.id,)).fetchall()
    return render_template('history.html', rows=rows)

@app.route('/report/<int:evaluation_id>.pdf')
@login_required
def report(evaluation_id):
    with db() as con: row=con.execute('SELECT * FROM evaluations WHERE id=? AND user_id=?',(evaluation_id,current_user.id)).fetchone()
    if not row: abort(404)
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    fd,tmp=tempfile.mkstemp(suffix='.pdf'); os.close(fd)
    doc=SimpleDocTemplate(tmp,pagesize=letter,rightMargin=0.65*inch,leftMargin=0.65*inch,topMargin=0.6*inch,bottomMargin=0.6*inch)
    styles=getSampleStyleSheet(); styles.add(ParagraphStyle(name='Brand',parent=styles['Title'],textColor=colors.HexColor('#6D4AFF'),fontSize=25,spaceAfter=5))
    story=[Paragraph('VOCALIQ / PERFORMANCE REPORT',styles['Brand']),Paragraph(row['title'],styles['Heading2']),Paragraph('Generated '+row['created_at'].replace('T',' '),styles['Normal']),Spacer(1,18)]
    data=[['OVERALL SCORE',f"{row['overall']:.1f} / 100"],['Pitch stability',f"{row['pitch']:.1f} / 100"],['Rhythm consistency',f"{row['rhythm']:.1f} / 100"],['Reference melody match',f"{row['reference_score']:.1f} / 100" if row['reference_score'] is not None else 'Not available'],['Lyrics similarity',f"{row['lyrics']:.1f} / 100" if row['lyrics'] is not None else 'Not available'],['Clip duration',f"{row['duration']:.1f} seconds"],['Estimated tempo',f"{row['bpm']:.0f} BPM"],['Median detected pitch',f"{row['median_pitch']:.1f} Hz"]]
    table=Table(data,colWidths=[2.7*inch,3.4*inch]); table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#6D4AFF')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('BACKGROUND',(0,1),(-1,-1),colors.HexColor('#F5F3FF')),('GRID',(0,0),(-1,-1),0.5,colors.white),('PADDING',(0,0),(-1,-1),9)])); story.extend([table,Spacer(1,18),Paragraph('COACH NOTES',styles['Heading2'])])
    for note in json.loads(row['feedback']): story.append(Paragraph('• '+note,styles['BodyText'])); story.append(Spacer(1,5))
    if row['reference_lyrics']: story.extend([Spacer(1,10),Paragraph('REFERENCE LYRICS',styles['Heading2']),Paragraph(row['reference_lyrics'].replace('&','&amp;').replace('<','&lt;').replace('>','&gt;'),styles['BodyText'])])
    story.extend([Spacer(1,20),Paragraph('Scoring note: when a reference track is provided, melody match uses approximate dynamic-time-warping alignment of detected pitch contours. Mixed vocals and instruments can reduce accuracy. Pitch stability and rhythm remain practice estimates. Results are intended for practice and are not a professional vocal assessment.',styles['Italic'])])
    doc.build(story)
    return send_file(tmp, as_attachment=True, download_name=f'vocaliq-report-{evaluation_id}.pdf', mimetype='application/pdf')

@app.errorhandler(413)
def too_large(e): flash('File is too large. Maximum upload size is 25 MB.','error'); return redirect(url_for('dashboard'))
if __name__=='__main__': app.run(debug=True, host='127.0.0.1', port=5000)
