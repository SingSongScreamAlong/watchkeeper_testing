# WATCHKEEPER Testing Edition

A lightweight AI-powered intelligence platform optimized for small-scale testing and proof-of-concept validation on older hardware (2014 Mac Mini).

## Overview

WATCHKEEPER Testing Edition is designed for alpha testing with 3-5 missionary teams, processing 50-100 articles per day from European news sources. It uses a lightweight tech stack with FastAPI, SQLite, and Ollama (Llama 3.2 3B) to provide threat intelligence via API and WebSocket connections.

### Key Features

- **Lightweight Design**: Optimized for 2014 Mac Mini (Intel i5/i7, 8-16GB RAM)
- **AI-Powered Analysis**: Uses Ollama with Llama 3.2 3B for local AI processing
- **Sequential Processing**: Avoids overloading older hardware
- **Real-time Updates**: WebSocket support for instant threat notifications
- **Alpha Testing Tools**: Feedback collection and testing-specific endpoints
- **Performance Monitoring**: Resource usage tracking optimized for Mac Mini

## System Requirements

- **Hardware**: Mac Mini (2014 or newer) with Intel i5/i7 and 8-16GB RAM
- **Operating System**: macOS 10.15 (Catalina) or newer
- **Storage**: At least 10GB free space
- **Network**: Internet connection for news collection
- **Dependencies**: Python 3.8+, Ollama

## Installation

### Automated Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-organization/watchkeeper-testing.git
   cd watchkeeper-testing
   ```

2. Run the setup script:
   ```bash
   chmod +x setup_mac.sh
   ./setup_mac.sh
   ```

The setup script will:
- Create necessary directories
- Set up a Python virtual environment
- Install dependencies
- Install Ollama if not present
- Download the Llama 3.2 3B model
- Initialize the database
- Create a .env file with a random API key
- Optionally configure auto-start and optimize Mac Mini settings

### Manual Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install Ollama:
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```

5. Pull the Llama 3.2 3B model:
   ```bash
   ollama pull llama3.2:3b
   ```

6. Create a .env file:
   ```bash
   cp .env.example .env
   ```

7. Initialize the database:
   ```bash
   python -c "from src.core.database import init_db; import asyncio; asyncio.run(init_db())"
   ```

## Usage

### Starting the Application

Run the application:
```bash
./run_testing.py
```

Command line options:
- `--no-api`: Don't start the API server
- `--no-collection`: Don't run news collection
- `--no-monitor`: Don't run performance monitoring

### Accessing the API

The API is available at `http://localhost:8000` by default.

API documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Authentication

All API endpoints (except health checks) require an API key. Include the API key in the `X-API-Key` header:

```
X-API-Key: your-api-key-here
```

The API key is generated during setup and stored in the `.env` file.

## Project Structure

```
watchkeeper-testing/
├── data/                  # Data directory
│   └── logs/              # Log files
├── src/                   # Source code
│   ├── api/               # API endpoints
│   ├── collectors/        # News collectors
│   ├── core/              # Core components
│   ├── models/            # Database models
│   ├── services/          # Services
│   ├── utils/             # Utility functions
│   └── main.py            # FastAPI application
├── tests/                 # Tests
├── .env.example           # Example environment variables
├── README.md              # This file
├── requirements.txt       # Python dependencies
├── run_testing.py         # Runner script
└── setup_mac.sh           # Mac Mini setup script
```

## Configuration

Configuration is managed through environment variables in the `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLite database URL | `sqlite:///./data/threats.db` |
| `API_HOST` | API host | `0.0.0.0` |
| `API_PORT` | API port | `8000` |
| `API_KEY` | API key for authentication | Generated during setup |
| `OLLAMA_BASE_URL` | Ollama API URL | `http://localhost:11434` |
| `AI_MODEL` | AI model to use | `llama3.2:3b` |
| `AI_TIMEOUT` | AI request timeout in seconds | `30` |
| `PROCESSING_DELAY` | Delay between AI requests in seconds | `2` |
| `COLLECTION_FREQUENCY` | News collection frequency in minutes | `60` |
| `MAX_ARTICLES_PER_SOURCE` | Maximum articles to collect per source | `10` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `DEBUG` | Debug mode | `false` |
| `CORS_ORIGINS` | Allowed CORS origins | `["*"]` |

## News Sources

The system is configured to collect news from:
- BBC Europe
- Reuters Europe
- Deutsche Welle (DW)

To add or modify sources, use the API endpoints or directly modify the database.

## API Endpoints

### Threats

- `GET /api/threats`: List all threats with filtering options
- `GET /api/threats/{threat_id}`: Get a specific threat
- `GET /api/threats/stats`: Get threat statistics

### Health

- `GET /api/health`: Get system health status
- `GET /api/health/ai`: Check AI service status
- `GET /api/health/database`: Check database status
- `GET /api/health/resources`: Get system resource usage

### Testing

- `GET /api/testing/stats`: Get alpha testing statistics
- `POST /api/testing/feedback`: Submit alpha testing feedback
- `GET /api/testing/feedback`: List feedback submissions
- `POST /api/testing/trigger-collection`: Manually trigger news collection

### WebSocket

- `WebSocket /ws`: Real-time updates
- `WebSocket /ws/{client_id}`: Client-specific real-time updates

## WebSocket Subscriptions

Clients can subscribe to specific topics:
- `new_threats`: Receive notifications about new threats
- `system_status`: Receive system status updates
- `collection_status`: Receive news collection status updates

Example subscription:
```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws');

// Subscribe to topics
ws.onopen = () => {
  ws.send(JSON.stringify({
    action: 'subscribe',
    topics: ['new_threats', 'system_status']
  }));
};

// Handle messages
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};
```

## Testing Plan

### Phase 1: Basic Functionality (Week 1-2)
- Set up development environment on Mac Mini
- Test Ollama with Llama 3.2 3B model
- Implement and test news collectors
- Verify AI processing pipeline
- Test API endpoints with Postman/curl
- Verify WebSocket connectivity

### Phase 2: Integration Testing (Week 3-4)
- Connect SENTINEL to WATCHKEEPER APIs
- Test real-time updates via WebSocket
- Validate threat display on map
- Test mobile interface responsiveness
- Performance testing under load
- Error handling and recovery testing

### Phase 3: Alpha User Testing (Week 5-6)
- Deploy to 3-5 missionary families
- Collect user feedback via testing API
- Monitor system performance and reliability
- Document user satisfaction and feature requests
- Generate proof-of-concept validation report

## Performance Considerations

- **Sequential Processing**: News collection and AI processing are sequential to avoid overloading the CPU
- **Throttling**: AI requests are throttled with configurable delays
- **Resource Monitoring**: System resources are monitored to prevent overload
- **Database Optimization**: SQLite is configured with pragmas optimized for performance
- **Memory Management**: Connection pooling and resource cleanup to minimize memory usage

## Troubleshooting

### Common Issues

1. **Ollama Not Running**
   - Error: "Failed to connect to Ollama API"
   - Solution: Start Ollama with `ollama serve`

2. **Database Errors**
   - Error: "SQLite database is locked"
   - Solution: Ensure only one instance of the application is running

3. **High CPU Usage**
   - Issue: Mac Mini becomes unresponsive
   - Solution: Increase `PROCESSING_DELAY` in .env file

4. **API Key Issues**
   - Error: "Invalid API Key"
   - Solution: Check the API key in .env file and request headers

### Logs

Log files are stored in the `data/logs` directory:
- `watchkeeper.log`: Main application log
- `error.log`: Error log
- `performance.json`: Performance monitoring data

## License

[Your License Here]

## Contact

For support or questions, contact [Your Contact Information].
