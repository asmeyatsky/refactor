# Cloud Refactor Agent Frontend

This is a React-based frontend for the Universal Cloud Refactor Agent that enables users to migrate cloud services from AWS/Azure to GCP.

## Features

- Interactive interface for cloud service migration
- Support for multiple AWS and Azure services
- Code editor with example snippets
- Real-time migration status updates
- Comprehensive service mapping support

## Supported Services

### AWS Services
- S3 → Cloud Storage
- Lambda → Cloud Functions
- DynamoDB → Firestore
- SQS → Pub/Sub
- SNS → Pub/Sub
- RDS → Cloud SQL
- EC2 → Compute Engine
- CloudWatch → Cloud Monitoring
- API Gateway → Apigee
- EKS → GKE
- Fargate → Cloud Run

### Azure Services
- Blob Storage → Cloud Storage
- Functions → Cloud Functions
- Cosmos DB → Firestore
- Service Bus → Pub/Sub
- Event Hubs → Pub/Sub

## Prerequisites

- Node.js (v14 or higher)
- Python 3.7+ with pip
- The Cloud Refactor Agent backend must be running

## Installation

1. Install frontend dependencies:
```bash
cd frontend
npm install
```

2. Make sure the backend API server is running:
```bash
# From the project root directory
python api_server.py
```

3. Start the frontend development server:
```bash
cd frontend
npm start
```

The frontend will be available at `http://localhost:3000`

## Usage

1. Select the programming language of your code
2. Choose the cloud services you want to migrate
3. Paste your code in the editor or select from example snippets
4. Click "Migrate to GCP" to start the refactoring process
5. View the results in the migration panel

## API Integration

The frontend communicates with the backend API server at `http://localhost:8000` by default. You can configure this by setting the `REACT_APP_API_BASE_URL` environment variable:

```bash
REACT_APP_API_BASE_URL=http://your-api-server.com npm start
```

## Running in Production

To build the frontend for production:

```bash
npm run build
```

The built files will be available in the `build` directory, which can be served by any static file server.