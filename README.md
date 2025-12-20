# Topic-Centric SRS API

A modular Python REST API for Spaced Repetition System (SRS) using FastAPI with Supabase as the backend database.

## Features

- **Topic-based organization**: Organize flashcards by topics with SRS parameters (Stability, Difficulty)
- **Weighted card sampling**: Cards have intrinsic weights (0.5-2.0) for importance-based selection
- **Single-card probing**: One card per topic review with stochastic sampling using `random.choices()`
- **Effective scoring**: Card weight amplifies performance impact (effective_score = base_score × intrinsic_weight)
- **RESTful API**: Clean FastAPI endpoints for all operations
- **Advanced SRS algorithm**: Intelligent scheduling with difficulty modifiers and hours-based stability
- **Markdown support**: All text fields in cards support Markdown formatting for rich content
- **Supabase backend**: Cloud-hosted PostgreSQL database with realtime capabilities

## Tech Stack

- **FastAPI** - Modern, fast web framework for building APIs
- **Supabase** - Open source Firebase alternative (PostgreSQL + RESTful API)
- **Pydantic** - Data validation using Python type annotations
- **Uvicorn/Gunicorn** - ASGI server for production deployment
- **Docker** - Containerization for easy deployment

## Project Structure

```
TCSRS/
├── app/
│   ├── models/
│   │   └── schemas.py          # Pydantic models and schemas
│   ├── routers/
│   │   ├── decks.py            # Deck CRUD endpoints
│   │   ├── topics.py           # Topic CRUD endpoints
│   │   ├── cards.py            # Card CRUD endpoints
│   │   └── review.py           # Review/SRS endpoints
│   └── services/
│       ├── database.py         # Supabase database service
│       └── srs_engine.py       # SRS algorithm implementation
├── scripts/
│   ├── init_db.sql             # Database schema initialization
│   └── reset_db.py             # Database reset utility
├── main.py                     # FastAPI application entry point
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker configuration
├── .env.example                # Environment variables template
└── README.md                   # This file
```

## Setup

### 1. Prerequisites

- Python 3.11+
- Supabase account and project
- Docker (optional, for containerized deployment)

### 2. Installation

1. Clone the repository and navigate to the project directory:
```bash
cd TCSRS
```

2. Create a virtual environment and activate it:
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Configuration

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Update `.env` with your Supabase credentials:
```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_role_key
ENVIRONMENT=development
```

### 4. Database Setup

Initialize the database schema in Supabase:

**Option 1: Using Supabase SQL Editor**
1. Go to your Supabase project dashboard
2. Navigate to SQL Editor
3. Copy the contents of `scripts/init_db.sql`
4. Execute the SQL script

**Option 2: Using reset_db.py script**
```bash
python scripts/reset_db.py
```

Note: This will drop existing tables and recreate them.

## Running the API

### Development

```bash
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

### Production (using Gunicorn)

```bash
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Using Docker

1. Build the image:
```bash
docker build -t tcsrs-api .
```

2. Run the container:
```bash
docker run -p 8080:8080 --env-file .env tcsrs-api
```

## API Documentation

Once the server is running, visit:
- **Interactive API docs**: `http://localhost:8000/docs`
- **Alternative docs**: `http://localhost:8000/redoc`

## API Endpoints

### Decks
- `POST /decks/` - Create a new deck
- `GET /decks/` - Get all decks (optionally filter by user_id)
- `GET /decks/{deck_id}` - Get a specific deck
- `PATCH /decks/{deck_id}` - Update a deck
- `DELETE /decks/{deck_id}` - Delete a deck

### Topics
- `POST /topics/` - Create a new topic
- `GET /topics/deck/{deck_id}` - Get all topics in a deck
- `GET /topics/due` - Get topics due for review
- `GET /topics/{topic_id}` - Get a specific topic
- `PATCH /topics/{topic_id}` - Update a topic
- `DELETE /topics/{topic_id}` - Delete a topic

### Cards
- `POST /cards/` - Create a new card (QA or Multiple Choice)
- `GET /cards/topic/{topic_id}` - Get all cards for a topic
- `GET /cards/{card_id}` - Get a specific card
- `PATCH /cards/{card_id}` - Update a card's intrinsic weight
- `DELETE /cards/{card_id}` - Delete a card

### Review
- `GET /review/topics/{topic_id}/review-card` - Get a random weighted card for review
- `POST /review/topics/{topic_id}/submit-review` - Submit review and update SRS parameters

## SRS Algorithm

The algorithm implements topic-based scheduling with single-card stochastic probing:

### Parameters
- **Stability**: Memory retention time in hours (min: 2.4h, max: 8760h/365 days)
- **Difficulty**: Topic difficulty rating (1-10)
- **Intrinsic Weight**: Card importance (0.5-2.0)
- **Base Score**: Review rating (0=Again, 1=Hard, 2=Good, 3=Easy)

### Update Rules

**Stability Update:**
```
If base_score == 0 (Again):
    S = max(2.4 hours, S × 0.5)
Else:
    effective_score = base_score × intrinsic_weight
    S = S × (1 + effective_score × 0.15)
```

**Difficulty Update:**
```
effective_score = base_score × intrinsic_weight
D = D - (effective_score - 2.0) × 0.3
```

**Next Review:**
```
difficulty_modifier = 1 + (D - 5) × 0.12
next_review = now + (stability × difficulty_modifier) hours
```

## Deployment to Google Cloud Run

1. Build and tag the Docker image:
```bash
docker build -t gcr.io/YOUR_PROJECT_ID/tcsrs-api .
```

2. Push to Google Container Registry:
```bash
docker push gcr.io/YOUR_PROJECT_ID/tcsrs-api
```

3. Deploy to Cloud Run:
```bash
gcloud run deploy tcsrs-api \
  --image gcr.io/YOUR_PROJECT_ID/tcsrs-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars SUPABASE_URL=your_url,SUPABASE_KEY=your_key
```

Alternatively, use the Google Cloud Console to deploy from the container image.

## Example Usage

### 1. Create a Deck
```bash
curl -X POST "http://localhost:8000/decks/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Spanish Vocabulary",
    "user_id": "user123",
    "description": "Basic Spanish words and phrases"
  }'
```

### 2. Create a Topic
```bash
curl -X POST "http://localhost:8000/topics/" \
  -H "Content-Type: application/json" \
  -d '{
    "deck_id": "deck-uuid",
    "name": "Common Verbs",
    "stability": 24.0,
    "difficulty": 5.0
  }'
```

### 3. Create Cards
```bash
# QA Card
curl -X POST "http://localhost:8000/cards/" \
  -H "Content-Type: application/json" \
  -d '{
    "topic_id": "topic-uuid",
    "card_type": "qa_hint",
    "question": "What is **hablar** in English?",
    "answer": "to speak",
    "hint": "Starts with 's'",
    "intrinsic_weight": 1.2
  }'

# Multiple Choice Card
curl -X POST "http://localhost:8000/cards/" \
  -H "Content-Type: application/json" \
  -d '{
    "topic_id": "topic-uuid",
    "card_type": "multiple_choice",
    "question": "What does **comer** mean?",
    "choices": ["to drink", "to eat", "to sleep", "to run"],
    "correct_index": 1,
    "intrinsic_weight": 1.0
  }'
```

### 4. Review a Card
```bash
# Get a card for review
curl "http://localhost:8000/review/topics/topic-uuid/review-card"

# Submit review (base_score: 0=Again, 1=Hard, 2=Good, 3=Easy)
curl -X POST "http://localhost:8000/review/topics/topic-uuid/submit-review" \
  -H "Content-Type: application/json" \
  -d '{
    "base_score": 2
  }'
```

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
