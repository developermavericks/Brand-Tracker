# 📰 Brand-Tracker

An automated, self-hosted web application that monitors news RSS feeds for specific brands and companies in near real-time. It extracts full article text, performs local sentiment analysis, filters by region, deduplicates news using an SQLite database, and sends email notifications.

Developed & Maintained by **Satyam Kr Singh**.

---

## 📊 Visual System Diagrams

### 1. Application Workflow Flowchart
This diagram illustrates the step-by-step logic of the background news fetcher and the interactive Streamlit user interface:

```mermaid
graph TD
    A[Start: Scheduler / User Manual Fetch] --> B[Get tracked companies from SQLite]
    B --> C{For each company...}
    C --> D[Construct RSS search query based on Region]
    D --> E[Fetch RSS Feed from Google News]
    E --> F[Filter articles published within last 24 hours]
    F --> G{For each article...}
    G --> H[Check if article link exists in SQLite]
    H -- "Yes (Duplicate)" --> I[Skip article]
    H -- "No (New)" --> J[Resolve Google redirect using gnewsdecoder]
    J --> K[Fetch full content using newspaper3k & trafilatura]
    K --> L[Run Sentiment Analysis using TextBlob]
    L --> M[Save article to SQLite DB]
    M --> N[Collect new articles for notifications]
    N --> O{Any new articles found?}
    O -- "Yes" --> P[Send email digest via Gmail SMTP]
    O -- "No" --> Q[Update company fetch status in DB]
    P --> Q
    Q --> R[End of fetch cycle]
    
    S[Streamlit Web App] --> T[Read tracked companies & recent articles from SQLite]
    T --> U[Display interactive UI dashboard with search/filters/IST conversion]
    U --> V[Generate & Download Excel Brand Reports]
```

### 2. System Architecture
The relationship between frontend, backend modules, database, and external resources:

```mermaid
graph LR
    subgraph Streamlit Frontend
        UI["Web Dashboard (app.py)"]
    end

    subgraph Core Backend
        Scheduler["Background Scheduler (scheduler.py)"]
        Fetcher["News Fetcher Module (fetcher.py)"]
        NLP["TextBlob Sentiment Engine"]
        SMTP["Gmail SMTP Notifier (notifier.py)"]
    end

    subgraph Storage
        DB[("SQLite Database (news_tracker.db)")]
    end

    subgraph External Services
        GNews["Google News RSS Feed"]
        SMTP_Server["Gmail SMTP Server"]
    end

    UI <--> DB
    Scheduler --> Fetcher
    Fetcher <--> DB
    Fetcher --> GNews
    Fetcher --> NLP
    Fetcher --> SMTP
    SMTP --> SMTP_Server
```

### 3. Database Entity-Relationship Diagram (ERD)
The database structure stored in SQLite:

```mermaid
erDiagram
    COMPANIES {
        int id PK
        string name UNIQUE
        string region "Global / India / Both"
        string last_status "Logs of last fetch status"
    }
    ARTICLES {
        int id PK
        int company_id FK
        string title
        string link UNIQUE
        string published_at
        string source
        string summary "Stores extracted full article text"
        string sentiment "Positive / Negative / Neutral"
        string extraction_method "summary / full"
        timestamp created_at
    }
    COMPANIES ||--o{ ARTICLES : tracks
```

---

## 🚀 Key Features

* **Automated Scraper & Scheduler**: Runs in the background (every 5-10 mins) to pull the latest news from Global and regional RSS feeds.
* **Content Extraction & Deduplication**: Fetches full article content dynamically and stores details in SQLite to prevent duplicate alerts.
* **Local Sentiment Analysis**: Classifies article tones as Positive, Negative, or Neutral using TextBlob NLP.
* **Interactive Dashboard**: A clean UI to view, filter, and search articles in Indian Standard Time (IST) and Relative Time.
* **Excel Reports**: Download reports for any brand containing URLs, titles, news agencies, and publication times.
* **Gmail Alerts**: Dispatches automatic email digests when new articles are detected.

---

## 🛠️ Tech Stack

* **Frontend**: Streamlit
* **Database**: SQLite (built-in)
* **Scraping & NLP**: BeautifulSoup4, Newspaper3k, Trafilatura, TextBlob, googlenewsdecoder
* **Task Scheduling**: APScheduler
* **Exporting**: pandas, openpyxl
* **Configuration**: python-dotenv

---

## 📦 Prerequisites

- Python 3.9 or higher.
- A Gmail account with **App Passwords** enabled for sending emails (optional).
  - To generate an app password, go to [Google Account > Security > App Passwords](https://myaccount.google.com/apppasswords).

---

## ⚙️ Setup & Local Execution

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables (Optional)
If you want to receive email alerts, create a `.env` file in the root directory based on the `.env.example` file:
```env
GMAIL_USER=your_email@gmail.com
GMAIL_PASS=xxxx xxxx xxxx xxxx
GMAIL_RECEIVER=receiver_email@gmail.com
```
*Note: If these environment variables are missing, the scraper and dashboard will work perfectly, but email notifications will be skipped.*

### 3. Run the Application
```bash
streamlit run app.py
```
The database gets automatically initialized on first run as `news_tracker.db`. The background scheduler will automatically start and check for news updates every 5 minutes.

---

## 👨‍💻 Author & Lead Developer

* **Satyam Kr Singh**
  * Git Branch: `satyam`
  * Repository: [developermavericks/Brand-Tracker](https://github.com/developermavericks/Brand-Tracker)
