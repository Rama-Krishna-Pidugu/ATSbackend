# PeopleGPT API

An AI-powered talent acquisition and screening platform built with FastAPI.

## Features

- Resume parsing and information extraction
- Semantic search for candidates using FAISS
- AI-generated screening questions using Groq
- Personalized outreach email generation using Groq
- Background check integration (mock implementation)

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory:
```
GROQ_API_KEY=your_groq_api_key_here
ENV=development
DB_HOST=
DB_NAME=
DB_PASSWORD=
DB_USER=
COMPANY_NAME=

POSITION_TITLE=Python Developer

SMTP_HOST=smtp.gmail.com
SMTP_PORT=
SMTP_USER=
SMTP_PASS=
SENDER_EMAIL=

S3_BUCKET=
CLERK_JWT_PUBLIC_KEY=
clerk_issue_token_url=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=
```

4. Run the application:
```bash
uvicorn app.main:app --reload

uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, visit `http://localhost:8000/docs` for interactive API documentation.

### Available Endpoints

#### Resume Management
- `POST /api/v1/upload-resume/` - Upload and parse a resume

#### Candidate Search
- `POST /api/v1/search/` - Search for candidates
- `POST /api/v1/add-candidate/` - Add a new candidate
- `DELETE /api/v1/clear-index/` - Clear the search index

#### Screening
- `POST /api/v1/generate-questions/` - Generate screening questions

#### Email Generation
- `POST /api/v1/generate-email/` - Generate personalized outreach email

#### Background Check
- `POST /api/v1/check/` - Perform background check
- `POST /api/v1/add-record/` - Add a record to the mock database

## Example API Calls



### Upload Resume
```bash
curl -X POST "http://localhost:8000/api/v1/upload-resume/" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@resume.pdf"
```

### Search Candidates
```bash
curl -X POST "http://localhost:8000/api/v1/search/" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{"query": "Python developers in Bangalore", "location": "Bangalore", "experience_years": 5}'
```

### Generate Screening Questions
```bash
curl -X POST "http://localhost:8000/api/v1/generate-questions/" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{"skill": "Python", "level": "senior"}'
```

### Generate Email
```bash
curl -X POST "http://localhost:8000/api/v1/generate-email/" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "skill": "Python", "company_name": "TechCorp", "position": "Senior Developer"}'
```

### Background Check
```bash
curl -X POST "http://localhost:8000/api/v1/check/" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "location": "Bangalore"}'
```

## Project Structure

```
peoplegpt/
│
├── app/
│   ├── main.py
│   ├── models.py
│   ├── routes/
│   │   ├── resume.py
│   │   ├── search.py
│   │   ├── screen.py
│   │   ├── email.py
│   │   └── background.py
│   └── services/
│       ├── resume_parser.py
│       ├── search_engine.py
│       ├── screening_generator.py
│       ├── email_generator.py
│       ├── background_check.py
│       └── llm_utils.py
│
├── data/
│   ├── resumes/
│   └── faiss_index/
│
├── requirements.txt
└── README.md
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License 
