# Mini CRM Backend API - Agentic AI Edition

A FastAPI backend for the Mini CRM application with advanced agentic AI features, enhanced lead management, document processing with Tesseract OCR, intelligent LLM interactions, and React Flow workflow automation.

## 🚀 Enhanced Features

- **🧾 Agentic Lead Management**: Create, read, update, and delete leads with intelligent validation
- **📄 Tesseract OCR Document Processing**: Extract lead information from PDF and image files using Tesseract OCR
- **🤖 Enhanced LLM Integration**: Context-aware AI-powered lead interaction and assistance
- **🔁 React Flow Workflow Designer**: Visual workflow builder with node execution and persistence
- **✅ Advanced Validation**: Email validation, input sanitization, and error handling
- **📊 Workflow Persistence**: Save and manage multiple workflows with execution logs
- **🔄 CORS Support**: Compatible with React frontend
- **💾 Data Persistence**: JSON file storage with in-memory caching

## �� Prerequisites

### System Requirements
- **Python 3.11+**
- **Node.js 16+**
- **Tesseract OCR** (must be installed and in PATH)
- **RAM**: 16GB+ (32GB+ recommended)
- **Storage**: 20GB+ free space

## 🛠️ Installation

1. **Clone or navigate to the backend directory**
   ```bash
   cd backend
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**
   
   **Windows:**
   ```bash
   venv\Scripts\activate
   ```
   
   **macOS/Linux:**
   ```bash
   source venv/bin/activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

#### Install Tesseract Binary
- **Windows:** Download and install from https://github.com/tesseract-ocr/tesseract/wiki
- **Linux:** `sudo apt install tesseract-ocr`

## 🏃‍♂️ Running the Server

Start the development server:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API Base URL**: http://localhost:8000
- **Interactive Documentation**: http://localhost:8000/docs
- **Alternative Documentation**: http://localhost:8000/redoc

## 📚 Enhanced API Endpoints

### 🧾 Lead Management with Agentic AI

#### 1. Create Lead Manually (Enhanced)
```http
POST /leads/manual
Content-Type: application/json

{
  "name": "John Doe",
  "email": "john.doe@example.com",
  "phone": "+1 (555) 123-4567"
}
```

**Features:**
- Email format validation using regex
- Input sanitization
- Automatic status and source assignment

#### 2. Create Lead from Document (Tesseract OCR)
```http
POST /leads/document
Content-Type: multipart/form-data

file: [PDF or Image file]
```

**Features:**
- Tesseract OCR integration
- Email validation and fallback
- Confidence scoring
- Extraction notes
- Temporary file management

**Response:**
```json
{
  "name": "Extracted Name",
  "email": "extracted@email.com",
  "phone": "N/A",
  "status": "New",
  "source": "Document",
  "confidence": 0.85,
  "extraction_notes": "Extraction successful"
}
```

#### 3. Get All Leads
```http
GET /leads
```

#### 4. Delete Lead
```http
DELETE /leads/{id}
```

#### 5. Update Lead Status
```http
PUT /leads/{id}/status
Content-Type: application/json

{
  "status": "Contacted"
}
```

### 🤖 Enhanced Lead Interaction (LLM)

#### 6. Interact with Lead (Context-Aware)
```http
POST /interact
Content-Type: application/json

{
  "id": 1,
  "prompt": "What are the details for this lead?"
}
```

**Enhanced LLM Responses:**
- **follow-up**: Email with current status
- **details**: Complete lead information
- **contact**: Contact information with best times
- **status**: Current status with timestamps
- **source**: Lead source information
- **next/action**: Contextual next actions based on status

**Response:**
```json
{
  "reply": "Name: John Doe, Email: john@example.com, Phone: +1 (555) 123-4567, Status: New, Source: Manual",
  "lead_context": {
    "id": 1,
    "name": "John Doe",
    "status": "New",
    "source": "Manual"
  }
}
```

### 🔁 React Flow Workflow Designer

#### 7. Execute Workflow (Enhanced)
```http
POST /workflow
Content-Type: application/json

{
  "name": "Lead Follow-up Workflow",
  "description": "Automated follow-up process",
  "nodes": [
    {
      "id": "trigger-1",
      "type": "trigger",
      "position": {"x": 100, "y": 100},
      "data": {"label": "Lead Created"}
    },
    {
      "id": "action-1",
      "type": "action",
      "position": {"x": 300, "y": 100},
      "data": {"label": "Send Welcome Email"}
    }
  ],
  "edges": [
    {
      "id": "edge-1",
      "source": "trigger-1",
      "target": "action-1"
    }
  ]
}
```

**Features:**
- Workflow structure validation
- Maximum 3 action nodes
- Lead Created trigger requirement
- Connected node validation
- Execution logging with timestamps
- Workflow persistence

**Response:**
```json
{
  "message": "Workflow executed successfully",
  "workflow_id": "workflow-1703123456789",
  "execution_log": [
    "[2024-01-15T10:30:00] Trigger node: Lead Created",
    "[2024-01-15T10:30:01] Email triggered: Send Welcome Email",
    "[2024-01-15T10:30:02] Connection: trigger-1 -> action-1"
  ]
}
```

#### 8. Get All Workflows
```http
GET /workflows
```

#### 9. Delete Workflow
```http
DELETE /workflows/{workflow_id}
```

### Utility Endpoints

#### Health Check (Enhanced)
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00",
  "leads_count": 5,
  "workflows_count": 2
}
```

#### API Information
```http
GET /
```

## 🧪 Testing with Postman

### 1. Create a Lead Manually (Enhanced)
- **Method**: POST
- **URL**: `http://localhost:8000/leads/manual`
- **Headers**: `Content-Type: application/json`
- **Body**:
```json
{
  "name": "Jane Smith",
  "email": "jane.smith@company.com",
  "phone": "+1 (555) 987-6543"
}
```

### 2. Upload Document with Tesseract OCR
- **Method**: POST
- **URL**: `http://localhost:8000/leads/document`
- **Body**: Form-data with file upload

### 3. Enhanced LLM Interaction
- **Method**: POST
- **URL**: `http://localhost:8000/interact`
- **Headers**: `Content-Type: application/json`
- **Body**:
```json
{
  "id": 1,
  "prompt": "next action"
}
```

### 4. Execute Workflow
- **Method**: POST
- **URL**: `http://localhost:8000/workflow`
- **Headers**: `Content-Type: application/json`
- **Body**: (See workflow example above)

## 🔧 Configuration

### CORS Settings
The API is configured to accept requests from:
- `http://localhost:3000`
- `http://127.0.0.1:3000`
- `http://localhost:4028`

### Data Storage
- **Leads**: Stored in `leads.json`
- **Workflows**: Stored in `workflow.json`
- **Uploads**: Temporary files in `uploads/` directory
- In-memory caching for better performance
- Automatic data persistence

### Validation Rules
- **Email**: Regex pattern `[\w\.-]+@[\w\.-]+\.\w+`
- **Name**: Non-empty, trimmed
- **Phone**: Non-empty, trimmed
- **Workflow**: Maximum 3 action nodes, Lead Created trigger required

## 📁 Project Structure

```
backend/
├── main.py              # FastAPI application with agentic features
├── models.py            # Enhanced Pydantic models with validation
├── utils.py             # Utility functions for OCR, validation, etc.
├── leads.json           # Lead data storage
├── workflow.json        # Workflow data storage
├── uploads/             # Temporary file storage
├── requirements.txt     # Dependencies
└── README.md           # This file
```

## 🔍 Enhanced API Response Examples

### Lead Response (Enhanced)
```json
{
  "id": 1,
  "name": "John Doe",
  "email": "john.doe@example.com",
  "phone": "+1 (555) 123-4567",
  "status": "New",
  "source": "Manual",
  "created_at": "2024-01-15T10:30:00"
}
```

### Document Extraction Response (Tesseract OCR)
```json
{
  "name": "Sarah Johnson",
  "email": "sarah.johnson@techcorp.com",
  "phone": "N/A",
  "status": "New",
  "source": "Document",
  "confidence": 0.85,
  "extraction_notes": "Extraction successful"
}
```

### LLM Interaction Response (Context-Aware)
```json
{
  "reply": "Next action for John Doe: Send welcome email and schedule initial call",
  "lead_context": {
    "id": 1,
    "name": "John Doe",
    "status": "New",
    "source": "Manual"
  }
}
```

## 🚨 Enhanced Error Handling

The API returns appropriate HTTP status codes with detailed error messages:
- `200`: Success
- `400`: Bad Request (validation errors)
- `404`: Not Found
- `422`: Unprocessable Entity (extraction failures)
- `500`: Internal Server Error

Error responses include detailed information:
```json
{
  "error": "Validation failed",
  "details": "Invalid email format",
  "timestamp": "2024-01-15T10:30:00"
}
```

## 🔐 Security Notes

- This is a development setup
- For production, implement proper authentication
- Enhanced input validation and sanitization
- Use environment variables for sensitive data
- Temporary file cleanup implemented

## 🐛 Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Kill process on port 8000
   lsof -ti:8000 | xargs kill -9
   ```

2. **Import errors**
   ```bash
   # Reinstall dependencies
   pip install -r requirements.txt --force-reinstall
   ```

3. **CORS issues**
   - Ensure frontend is running on supported ports
   - Check browser console for CORS errors

4. **File upload issues**
   - Check `uploads/` directory permissions
   - Ensure sufficient disk space

### Logs
The API logs all operations with enhanced detail:
- Lead creation with validation results
- Tesseract OCR processing steps
- LLM interaction context
- Workflow execution logs

## 📞 Support

For issues and questions:
1. Check the enhanced logs in the terminal
2. Verify all dependencies are installed
3. Ensure the virtual environment is activated
4. Test with the interactive documentation at `/docs`
5. Check workflow validation rules

## 🔄 Integration with Frontend

This enhanced backend is designed to work seamlessly with the React frontend. The agentic AI features provide:
- Intelligent lead validation
- Context-aware interactions
- Workflow persistence and execution
- Enhanced error handling

---

**Happy coding with Agentic AI! 🚀🤖** 

## 🔄 Tesseract OCR Integration

### AI-Powered OCR
- **Tesseract OCR Integration**: Uses Tesseract for document text extraction
- **Multi-format Support**: PDF, PNG, JPG, JPEG
- **Fast Processing**: Optimized for speed with memory management

#### Test Tesseract OCR Setup
```bash
python
>>> import pytesseract
>>> from PIL import Image
>>> img = Image.open('resume_optimized.png')
>>> print(pytesseract.image_to_string(img))
```
---
### Team:
1. Gayathri Parsam
2. Niharika Peela
3. Divya Bandla
4. T. Vineeth Kumar

