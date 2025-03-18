# 📽️ Video Analysis and Summary

**AI-powered tool to analyze and summarize video content from YouTube links or uploaded video files.** It provides concise summaries, sentiment analysis, keyword extraction, and transcript generation.

## 🌍 Live Demo  

🔗 **Project Working Link:** [Click Here](https://huggingface.co/spaces/AmritSbisht/QuickVid_AI_-_Video_Analysis_and_Summary)

## 🚀 Features

✅ **YouTube Video Summarization** – Extracts and summarizes YouTube videos via URL.  
✅ **Video File Processing** – Upload and analyze any video file for insights.  
✅ **Customizable Summaries** – Supports markdown, bullet, or narrative formats.  
✅ **Multi-Language Support** – Generates summaries in multiple languages.  
✅ **Sentiment Analysis** – Evaluates the emotional tone of the video.  
✅ **Keyword Extraction** – Identifies key topics covered in the content.  
✅ **Export Options** – Download summaries as **TXT, MD, or JSON**.  
✅ **History Management** – Stores previous summaries for quick access.  

## 🛠️ Tech Stack

- **Frontend:** Streamlit  
- **Backend:** FastAPI  
- **AI Model:** Gemini API (Google's LLM)  
- **Speech Recognition:** Google Speech Recognition API  
- **Sentiment Analysis:** NLTK's VADER  
- **Database:** SQLite (optional for history storage)  

## 📌 Installation

### Prerequisites  
Ensure you have **Python 3.8+** and **pip** installed.  

### Installation Steps  

1️⃣ **Clone the Repository**  
```sh
git clone https://github.com/yourusername/video-analysis-summary.git
cd video-analysis-summary
```  

2️⃣ **Create and Activate a Virtual Environment**  
```sh
python -m venv venv
venv\Scripts\activate  # For Windows
source venv/bin/activate  # For Mac/Linux
```  

3️⃣ **Install Dependencies**  
```sh
pip install -r requirements.txt
```  

## 🎬 Usage  

1️⃣ **Start the Backend Server**  
```sh
uvicorn backend:app --host 0.0.0.0 --port 8000
```  

2️⃣ **Run the Streamlit Frontend**  
```sh
streamlit run app.py
```  

3️⃣ **Access the Application**  
Open your browser and go to **`http://localhost:8501`**  

## 📡 API Endpoints  

| Method  | Endpoint            | Description                                |
|---------|---------------------|--------------------------------------------|
| `POST`  | `/summarize/youtube` | Summarize a YouTube video by URL          |
| `POST`  | `/summarize/upload`  | Upload a video file for summarization     |
| `GET`   | `/summaries`         | Fetch history of past summaries          |
| `DELETE`| `/summaries/{id}`    | Delete a summary from history            |
| `GET`   | `/health`            | Check API status                          |

## 🏗️ Project Structure  

```
📂 video-analysis-summary
│── 📂 backend/               # FastAPI backend
│   │── backend.py            # Main API server
│   │── models.py             # Data models
│   │── summarizer.py         # AI-based summarization logic
│   │── speech_to_text.py     # Speech recognition module
│   │── sentiment_analysis.py # Sentiment analysis module
│   │── requirements.txt      # Backend dependencies
│
│── 📂 frontend/              # Streamlit frontend
│   │── app.py                # Main Streamlit app
│   │── components.py         # UI components
│   │── styles.css            # Custom styling
│
│── 📂 data/                  # Storage for processed data
│── 📂 logs/                  # Logs for debugging
│── .gitignore                # Git ignore file
│── README.md                 # Project documentation
│── requirements.txt          # Global dependencies
```

## 👨‍💻 Contributing  

1. **Fork** the repository.  
2. **Clone** your fork:  
   ```sh
   git clone https://github.com/yourusername/video-analysis-summary.git
   ```  
3. **Create a new branch** for your feature:  
   ```sh
   git checkout -b feature-name
   ```  
4. **Make your changes & commit**:  
   ```sh
   git commit -m "Added new feature"
   ```  
5. **Push to GitHub & create a Pull Request**.  

## 📜 License  

This project is licensed under the **MIT License**.  

## 📩 Contact  

For any questions or suggestions, reach out at **amritsinghbist@gmail.com**.  
