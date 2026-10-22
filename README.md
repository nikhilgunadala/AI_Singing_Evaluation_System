# AI_Singing_Evaluation_System

# 🎤 VocalIQ Pro — AI-Based Singing Evaluation System

An AI-powered web application that evaluates singing performance by analyzing vocal pitch, rhythm, and lyric accuracy. VocalIQ Pro helps users understand their singing performance through visual analytics, personalized feedback, and downloadable evaluation reports.

## ✨ Features

- **User Authentication:** Secure registration, login, and logout.
- **Audio Recording:** Record singing directly through the browser.
- **Audio Upload:** Upload a recorded singing performance for evaluation.
- **Reference Song Comparison:** Compare a singing recording against an uploaded reference audio track.
- **Pitch Analysis:** Extract vocal pitch features and analyze pitch stability.
- **Rhythm Analysis:** Estimate tempo and evaluate timing-related features.
- **Lyrics Comparison:** Compare recognized or supplied lyrics with reference lyrics.
- **Weighted Scoring:** Combine evaluation metrics into an overall performance score.
- **Visual Analytics:** Explore pitch contours, comparison graphs, and score trends.
- **Score History:** Review previous evaluations and track performance.
- **Personalized Feedback:** Receive suggestions for improving singing practice.
- **PDF Reports:** Download evaluation results for future reference.
- **Responsive Interface:** Access the application through a modern, responsive web interface.

## 🛠️ Technology Stack

| Component | Technologies |
|---|---|
| Programming Language | Python |
| Backend Framework | Flask |
| Frontend | HTML, CSS, JavaScript |
| Database | SQLite |
| Audio Analysis | Librosa, NumPy |
| Speech Recognition | OpenAI Whisper |
| Audio Conversion | FFmpeg |
| Data Visualization | Chart.js |
| PDF Generation | ReportLab |
| Authentication | Flask-Login, password hashing |

## 🏗️ Project Structure

```text
VocalIQ-Pro/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── vocaliq.db
├── static/
│   ├── style.css
│   └── app.js
├── templates/
│   ├── base.html
│   ├── landing.html
│   ├── dashboard.html
│   ├── auth.html
│   ├── history.html
│   └── result.html
└── uploads/
    └── .gitkeep
```

> Note: The SQLite database and uploaded audio files are generated locally and should not be committed to a public repository. The structure above describes the main application components; filenames may vary by version.

## ⚙️ Prerequisites

Install the following before running the application:

- Python 3.11 recommended
- Git
- FFmpeg
- Visual Studio Code (recommended)

Download Python: https://www.python.org/downloads/

Download Git: https://git-scm.com/downloads

Download FFmpeg: https://ffmpeg.org/download.html

## 🚀 Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/nikhilgunadala/AI_Singing_Evaluation_System.git
cd AI_Singing_Evaluation_System
```

If the application files are inside a nested `vocaliq-pro` folder, enter it:

```bash
cd vocaliq-pro
```

Run this command only if that nested folder exists in the cloned repository.

### 2. Create a virtual environment

Windows:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use Command Prompt instead:

```cmd
.venv\Scripts\activate.bat
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Verify FFmpeg

```bash
ffmpeg -version
```

If the command is not recognized, install FFmpeg and add its `bin` directory to the Windows PATH environment variable. Restart the terminal after updating PATH.

### 5. Configure environment variables

For development, configure a secure Flask secret key through an environment variable rather than committing secrets to GitHub.

PowerShell example:

```powershell
$env:FLASK_SECRET_KEY = "replace-with-a-long-random-secret"
```

Use a different, securely generated secret in production.

### 6. Run the application

```bash
python app.py
```

Open the application in your browser:

http://127.0.0.1:5000

Create an account or sign in to access the evaluation dashboard.

## 🎼 How It Works

1. **Input:** The user uploads a singing recording or records audio in the browser.
2. **Preprocessing:** The audio is decoded, converted to a suitable sample rate, and prepared for analysis.
3. **Pitch Extraction:** Audio-processing algorithms estimate the vocal pitch contour.
4. **Rhythm Analysis:** Tempo and timing-related features are extracted from the recording.
5. **Lyrics Analysis:** Speech recognition can generate a transcript, which is compared with supplied reference lyrics when available.
6. **Reference Comparison:** When reference audio is supplied, pitch contours can be aligned using Dynamic Time Warping (DTW) to estimate melody similarity.
7. **Scoring:** Available metrics are combined into an overall singing evaluation score.
8. **Feedback:** The application presents analysis results, visual graphs, and improvement suggestions.
9. **History and Reports:** Evaluation results can be stored for the signed-in user and exported as PDF reports.

## 📊 Evaluation Metrics

| Metric | Purpose |
|---|---|
| Pitch Stability | Measures consistency in detected vocal pitch |
| Rhythm and Tempo | Estimates timing and rhythmic consistency |
| Lyrics Accuracy | Measures similarity between reference lyrics and recognized or supplied text |
| Melody Similarity | Estimates alignment between the singer's pitch contour and reference audio |
| Overall Score | Combines available metrics into a weighted score |

The availability and contribution of each metric depend on the inputs supplied and the evaluation implementation.

**Important:** These are practice-oriented estimates, not professional vocal assessments. Pitch tracking can be affected by instrumental accompaniment, background noise, harmonies, and recording quality. Speech recognition may also be inaccurate for sung lyrics.

## 🔐 Privacy and Security

- Passwords should be stored using secure password hashing.
- Keep secret keys and credentials in environment variables.
- Do not upload personal recordings, database files, or private user information to a public repository.
- Validate uploaded file types and sizes.
- Use HTTPS and production-grade configuration before public deployment.
- Restrict access to each user's evaluation history and reports.

## 🔮 Future Enhancements

- Real-time pitch tracking during singing
- Improved vocal and instrumental separation
- More accurate note-by-note melody comparison
- Advanced rhythm alignment and beat detection
- Support for multiple reference songs
- Vocal range and note distribution analysis
- Practice goals and progress tracking
- Exportable performance analytics
- Deployment to a cloud hosting platform

## 👨‍💻 Author

**Nikhil Gunadala**

GitHub: https://github.com/nikhilgunadala

## 📄 License

This project is intended for educational and portfolio purposes. Add an appropriate open-source license before permitting reuse or redistribution.

---

**VocalIQ Pro — Practice. Analyze. Improve.**
