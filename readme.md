# QueryX - AI-Powered Chat Assistant

QueryX is a full-stack AI chat application built with FastAPI (backend) and Next.js (frontend), featuring user authentication, conversation management, and document-based RAG (Retrieval-Augmented Generation).

## Features

- 🔐 **User Authentication** - JWT-based auth with secure httpOnly cookies
- 💬 **Real-time Chat** - Interactive chat interface with conversation history
- 📚 **RAG System** - Document crawling and vector-based knowledge retrieval
- 🔄 **Message Queuing** - RabbitMQ for reliable message processing
- ⚡ **Hot Caching** - Redis for fast message retrieval
- 🎯 **Batch Processing** - Support for batch API calls
- 📱 **Responsive UI** - Modern interface built with Chakra UI

## Architecture

```
QueryX/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API endpoints (auth, chat, documents)
│   │   │   └── utils/          # Utilities and logging
│   │   └── scripts/            # Database and utility scripts
├── frontend/               # Next.js frontend
│   ├── app/                # App Router pages
│   ├── src/                # Components and utilities
│   └── public/             # Static assets
└── docs/                   # Documentation
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for RabbitMQ and Redis)
- OpenAI API key

### 1. Clone and Setup Environment

```bash
git clone <your-repo-url>
cd QueryX
cp env.example .env
# Edit .env with your OpenAI API key and other settings
```

### 2. Start Infrastructure Services

```bash
# Start RabbitMQ
docker run -d \
  --hostname my-rabbit \
  --name rabbitmq \
  -p 5672:5672 \
  -p 15672:15672 \
  rabbitmq:3-management

# Start Redis
docker run -d \
  --name redis \
  -p 6379:6379 \
  redis:latest
```

### 3. Setup Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create initial users
python scripts/create_users.py

# Start backend server
uvicorn app.main:app --reload --port 8000
```

### 4. Setup Frontend

```bash
cd frontend
npm install
npm run dev
```

### 5. Access the Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- RabbitMQ Management: http://localhost:15672 (guest/guest)

## Usage

### Authentication

1. **Register**: Visit `/register` to create a new account
2. **Sign In**: Use `/sign-in` to authenticate
3. **Chat**: Access the main chat interface at `/`

### API Endpoints

#### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login (sets httpOnly cookie)
- `GET /auth/me` - Get current user
- `POST /auth/logout` - Logout (clears cookie)

#### Chat
- `POST /api/chat` - Send single message
- `POST /api/chat/batch` - Send multiple messages
- `GET /api/conversations` - List user conversations

#### Documents
- `POST /api/documents/crawl` - Crawl and index documents

### Testing

#### Backend Tests
```bash
cd backend
python -m pytest app/tests/
```

#### Frontend Tests
```bash
cd frontend
npm test
```

#### Manual Testing with cURL
```bash
# Register user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"password123"}'

# Login and save cookie
curl -c cookies.txt -X POST http://localhost:8000/auth/login \
  -d "username=testuser&password=password123" \
  -H "Content-Type: application/x-www-form-urlencoded"

# Send chat message
curl -b cookies.txt -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"<user-id>","message":"Hello AI!"}'
```

## Configuration

Key environment variables in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `SECRET_KEY` | JWT secret key (32+ chars) | Required |
| `DATABASE_URL` | SQLite database path | `sqlite:///./conversations.db` |
| `RABBITMQ_URL` | RabbitMQ connection URL | `amqp://guest:guest@localhost:5672/%2F` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `CHAT_MODEL` | OpenAI model for chat | `gpt-4o-mini` |
| `NEXT_PUBLIC_BACKEND_URL` | Backend URL for frontend | `http://localhost:8000` |

## Development

### Project Structure

- **Backend (`/backend`)**:
  - `app/api/` - FastAPI route handlers
  - `app/core/` - Business logic (auth, chat, conversation handling)
  - `app/rag/` - RAG system and vector storage
  - `app/crawler/` - Document crawling and processing

- **Frontend (`/frontend`)**:
  - `app/` - Next.js 13+ App Router pages
  - `src/components/` - Reusable React components
  - `src/types/` - TypeScript type definitions

### Key Technologies

- **Backend**: FastAPI, SQLAlchemy, LangChain, FAISS, RabbitMQ, Redis
- **Frontend**: Next.js 13+, React, Chakra UI, TypeScript
- **Auth**: JWT with httpOnly cookies
- **AI**: OpenAI GPT models, text embeddings

## Deployment

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build
```

### Manual Deployment

1. Set up production environment variables
2. Configure reverse proxy (nginx)
3. Use process manager for backend (PM2, systemd)
4. Deploy frontend to Vercel/Netlify or static hosting

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes and add tests
4. Commit: `git commit -am 'Add feature'`
5. Push: `git push origin feature-name`
6. Create Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
- Create an issue on GitHub
- Check the documentation in `/docs`
- Review API documentation at `/docs` endpoint
