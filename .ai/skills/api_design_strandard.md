# DMRoot — API Design Standards

## 1. API Structure

Design REST APIs using resource-based endpoints. Follow consistent naming conventions, HTTP methods, and `/api/v1` versioning. Keep endpoints simple and feature-oriented. Avoid unnecessary endpoints and architectural complexity.

**Example:**
```http
GET    /api/v1/automations
POST   /api/v1/automations
GET    /api/v1/automations/{id}
PATCH  /api/v1/automations/{id}
DELETE /api/v1/automations/{id}
POST   /api/v1/automations/{id}/activate
```

## 2. Request Validation

Use FastAPI and Pydantic for request validation. Validate required fields, data types, formats, lengths, and allowed values. Keep business validation in the service layer. Never rely on frontend validation for security.

**Example:**
```python
from pydantic import BaseModel, Field

class AutomationCreate(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    trigger_type: str
    is_active: bool = False
```

## 3. Response Standards

Use centralized Pydantic response models and exception handlers inside core/ for all API responses.

Structure:

```
core/
├── responses.py           # Common response models
├── exceptions.py          # Custom exceptions
└── exception_handlers.py  # Global exception handlers

Response model (responses.py):

T = TypeVar("T")

class APIResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    error: dict | None = None
```

Rules:

Reuse common response models across all modules.
Handle errors centrally through FastAPI exception handlers.
Use meaningful error codes and correct HTTP status codes.
Never expose internal errors or stack traces.
Avoid feature-specific response structures.

## AI Implementation Rules

- Follow these standards for every API.
- Maintain consistency across all feature modules.
- Avoid duplicating validation and response-handling logic.
- Use appropriate HTTP semantics.
- Do not introduce unnecessary abstractions.