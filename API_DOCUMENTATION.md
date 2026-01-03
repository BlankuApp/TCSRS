# Topic-Centric SRS API Documentation

**Base URL:** `http://localhost:8000`

---

## Table of Contents
- [Overview](#overview)
- [Environment Setup](#environment-setup)
- [Authentication](#authentication)
- [TypeScript Types](#typescript-types)
- [API Endpoints](#api-endpoints)
  - [Health Check](#health-check)
  - [Decks](#decks)
  - [Topics](#topics)
  - [Review](#review)
  - [Admin](#admin)
  - [AI Generation](#ai-generation)
- [SRS Algorithm & Review Workflow](#srs-algorithm--review-workflow)
- [Database Schema](#database-schema)
- [Integration Notes](#integration-notes)

---

## Overview

The **Topic-Centric SRS (Spaced Repetition System) API** is a REST API that implements an intelligent flashcard learning system using spaced repetition algorithms to optimize learning.

### Core Concept

The system organizes flashcards in a **three-level hierarchy**:
- **Decks** → **Topics** → **Cards**

**Key Architecture:**
- Cards are **embedded directly in topics** as a JSONB array (maximum 25 cards per topic)
- Cards do not have separate IDs or timestamps - they are indexed by position (0-24)
- Each card has an **intrinsic weight** (0.5-2.0) representing its importance

During reviews, the system:
1. Uses **weighted stochastic sampling** to select one card per topic
2. Amplifies review performance by card importance: `effective_score = base_score × intrinsic_weight`
3. Updates topic **stability** (memory retention) and **difficulty** parameters
4. Schedules the next review using hours-based intervals

### Tech Stack
- **FastAPI** - Python web framework
- **Supabase** - PostgreSQL with Row-Level Security (RLS) and JSONB support
- **JWT Authentication** - Token-based security
- **Markdown Support** - Rich text formatting in card content

---

## Environment Setup

### Required Environment Variables

Create a `.env.local` file in your Next.js project:

```env
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000

# Supabase Configuration (for authentication)
NEXT_PUBLIC_SUPABASE_URL=https://mlubbzyctgiafjbiqyfo.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

### CORS Configuration

The API is configured to accept requests from `http://localhost:3000` by default. For production deployments, update the `FRONTEND_URL` environment variable on the backend.

### Testing the Connection

Verify the API is running:
```bash
curl http://localhost:8000/health
# Expected: {"status": "healthy"}
```

### Interactive API Documentation

For testing endpoints during development:
- **Swagger UI**: http://localhost:8000/docs

---

## Authentication

All endpoints except health checks require **JWT Bearer token authentication**.

### Header Format
```
Authorization: Bearer <your_jwt_token>
```

### Authentication Flow

1. User authenticates with **Supabase** (using Supabase client in Next.js)
2. Supabase returns a JWT token
3. Include the token in the `Authorization` header for all API requests
4. The API validates the token and enforces Row-Level Security (RLS)

### Example with Fetch
```typescript
const token = supabaseSession.access_token;

const response = await fetch('http://localhost:8000/decks/', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});
```

### Error Responses

- **401 Unauthorized**: Missing or invalid token
- **403 Forbidden**: Insufficient permissions (e.g., non-admin accessing admin routes)

---

## TypeScript Types

### Core Data Models

```typescript
// Deck
interface Deck {
  id: string;                    // UUID
  name: string;                  // 1-255 characters
  prompt: string;                // Deck prompt (mandatory)
  user_id: string;               // UUID
  created_at: string | null;     // ISO 8601 datetime
  updated_at: string | null;     // ISO 8601 datetime
}

// Card Item (embedded in topic, no id/timestamps)
interface CardItem {
  card_type: 'qa_hint' | 'multiple_choice';
  intrinsic_weight: number;      // Range: 0.5-2.0, default: 1.0
  card_data: QAHintData | MultipleChoiceData;
}

// QA Hint Card Data
interface QAHintData {
  question: string;              // Markdown supported
  answer: string;                // Markdown supported
  hint: string;                  // Markdown supported, default: ''
}

// Multiple Choice Card Data
interface MultipleChoiceData {
  question: string;              // Markdown supported
  choices: string[];             // Min 2 items, Markdown supported
  correct_index: number;         // 0-based index
  explanation: string;           // Default: '', shown after user answers, Markdown supported
}

// Topic with embedded cards
interface Topic {
  id: string;                    // UUID
  deck_id: string;               // UUID
  name: string;                  // 1-255 characters
  cards: CardItem[];             // Embedded cards array (max 25)
  stability: number;             // Hours (2.4 - 8760), default: 24.0
  difficulty: number;            // Range: 1-10, default: 5.0
  next_review: string;           // ISO 8601 datetime
  last_reviewed: string | null;  // ISO 8601 datetime
  created_at: string | null;
  updated_at: string | null;
}

// Topic List Response (Paginated)
interface TopicListResponse {
  items: Topic[];                // Topics on current page
  total: number;                 // Total number of topics in deck
  page: number;                  // Current page number (1-based)
  page_size: number;             // Items per page
  total_pages: number;           // Total number of pages
  has_next: boolean;             // Whether there is a next page
  has_prev: boolean;             // Whether there is a previous page
}

// Review Card Item (includes topic_id and card_index for tracking)
interface ReviewCardItem {
  topic_id: string;              // Parent topic UUID
  card_index: number;            // Index in topic.cards array (0-24)
  card_type: 'qa_hint' | 'multiple_choice';
  intrinsic_weight: number;
  card_data: QAHintData | MultipleChoiceData;
}

// Deck Review Response
interface DeckReviewResponse {
  cards: ReviewCardItem[];       // List of cards to review (max 100)
  total_due: number;             // Total number of due topics in deck
  deck_id: string;               // ID of the deck being reviewed
}

// Review Submission
interface ReviewSubmission {
  base_score: 0 | 1 | 2 | 3;     // 0=Again, 1=Hard, 2=Good, 3=Easy
}

// Review Response
interface ReviewResponse {
  topic_id: string;
  card_index: number;            // Index of reviewed card
  new_stability: number;         // Hours
  new_difficulty: number;        // 1-10
  next_review: string;           // ISO 8601 datetime
  message: string;
}
```

### Request Types

```typescript
// Create Deck
interface CreateDeckRequest {
  name: string;                  // Required, 1-255 chars
  prompt: string;                // Required, deck prompt
}

// Update Deck
interface UpdateDeckRequest {
  name?: string;                 // 1-255 chars
  prompt?: string;               // Deck prompt
}

// Create Topic
interface CreateTopicRequest {
  deck_id: string;               // Required, UUID
  name: string;                  // Required, 1-255 chars
  stability?: number;            // Default: 24.0, > 0
  difficulty?: number;           // Default: 5.0, range: 1-10
}

// Update Topic
interface UpdateTopicRequest {
  name?: string;                 // 1-255 chars
  stability?: number;            // > 0
  difficulty?: number;           // 1-10
}

// Create QA Hint Card (added to topic)
interface CreateQAHintCardRequest {
  card_type: 'qa_hint';
  question: string;              // Required, min 1 char
  answer: string;                // Required, min 1 char
  hint?: string;                 // Default: ''
  intrinsic_weight?: number;     // Default: 1.0, range: 0.5-2.0
}

// Create Multiple Choice Card (added to topic)
interface CreateMultipleChoiceCardRequest {
  card_type: 'multiple_choice';
  question: string;              // Required, min 1 char
  choices: string[];             // Required, min 2 items
  correct_index: number;         // Required, >= 0
  explanation?: string;          // Default: '', shown after user answers
  intrinsic_weight?: number;     // Default: 1.0, range: 0.5-2.0
}

// Union type for card creation
type CreateCardRequest = CreateQAHintCardRequest | CreateMultipleChoiceCardRequest;

// Update Card (at specific index)
interface UpdateCardRequest {
  intrinsic_weight?: number;     // Range: 0.5-2.0
  question?: string;             // Min 1 char
  answer?: string;               // Min 1 char (QA cards only)
  hint?: string;                 // QA cards only
  choices?: string[];            // Min 2 items (Multiple Choice only)
  correct_index?: number;        // >= 0 (Multiple Choice only)
  explanation?: string;          // Multiple Choice only
}

// Admin - Update User Role
interface UpdateUserRoleRequest {
  role: 'user' | 'pro' | 'admin'; // Target role
}

interface UpdateUserRoleResponse {
  user_id: string;               // UUID of updated user
  role: string;                  // New role
  message: string;               // Success message
}

// User Info (Admin)
interface UserInfo {
  id: string;                    // UUID of user
  email: string;                 // User email address
  username: string;              // Display name (default: "User")
  avatar: string | null;         // Avatar URL (can be null)
  role: string;                  // User role: 'user', 'pro', or 'admin'
  created_at: string;            // ISO 8601 datetime
}

// User List Response (Paginated)
interface UserListResponse {
  items: UserInfo[];             // Users on current page
  total: number;                 // Total number of users (after filtering)
  page: number;                  // Current page number (1-based)
  page_size: number;             // Items per page
  total_pages: number;           // Total number of pages
  has_next: boolean;             // Whether there is a next page
  has_prev: boolean;             // Whether there is a previous page
}

// AI Provider Types
type AIProvider = 'openai' | 'google' | 'xai' | 'anthropic';

interface AIModel {
  id: string;                    // Model identifier (e.g., 'gpt-4o')
  name: string;                  // Display name (e.g., 'GPT-4o')
}

interface AIProviderInfo {
  id: string;                    // Provider identifier
  display_name: string;          // Display name
  models: AIModel[];             // Available models
}

interface AIProvidersResponse {
  providers: AIProviderInfo[];   // List of available providers
  default_provider: string;      // Default provider ID
  default_model: string;         // Default model ID
}

// Generate Cards Request
interface GenerateCardsRequest {
  deck_prompt: string;           // Required, deck's prompt for card generation
  topic_name: string;            // Required, topic name to generate cards for
  provider: AIProvider;          // Required, AI provider to use
  model: string;                 // Required, model ID to use
  api_key?: string;              // Optional, if empty and user is pro/admin, uses server-side key
}

// Generated Card
interface GeneratedCard {
  card_type: 'qa_hint' | 'multiple_choice';
  question: string;              // Markdown supported
  answer?: string;               // For qa_hint cards
  hint?: string;                 // For qa_hint cards
  choices?: string[];            // For multiple_choice cards
  correct_index?: number;        // For multiple_choice cards
  explanation?: string;          // For multiple_choice cards
}

// Generate Cards Response
interface GenerateCardsResponse {
  cards: GeneratedCard[];        // List of generated cards
}
```

### Error Response

```typescript
interface ApiError {
  detail: string;
}
```

---

## API Endpoints

### Legend
- 🔒 = Authentication required
- 🔓 = No authentication required

---

### Health Check

#### `GET /` 🔓
Root health check

**Response:** `200 OK`
```typescript
{ message: string }
```

#### `GET /health` 🔓
Health check endpoint

**Response:** `200 OK`
```typescript
{ status: string }
```

---

### Decks

#### `POST /decks/` 🔒
Create a new deck

**Request Body:** `CreateDeckRequest`

**Response:** `201 Created` → `Deck`

**Errors:**
- `400` - Validation error
- `401` - Unauthorized

---

#### `GET /decks/` 🔒
Get all decks for the authenticated user

**Response:** `200 OK` → `Deck[]`

**Errors:**
- `401` - Unauthorized

---

#### `GET /decks/{deck_id}` 🔒
Get a specific deck by ID

**Path Parameters:**
- `deck_id` (string, UUID) - Deck ID

**Response:** `200 OK` → `Deck`

**Errors:**
- `401` - Unauthorized
- `404` - Deck not found

---

#### `PATCH /decks/{deck_id}` 🔒
Update a deck

**Path Parameters:**
- `deck_id` (string, UUID) - Deck ID

**Request Body:** `UpdateDeckRequest`

**Response:** `200 OK` → `Deck`

**Errors:**
- `400` - Validation error
- `401` - Unauthorized
- `404` - Deck not found

---

#### `DELETE /decks/{deck_id}` 🔒
Delete a deck and all its topics/cards

**Path Parameters:**
- `deck_id` (string, UUID) - Deck ID

**Response:** `204 No Content`

**Errors:**
- `401` - Unauthorized
- `404` - Deck not found

**Note:** This operation cascades to delete all associated topics and cards.

---

### Topics

#### `POST /topics/` 🔒
Create a new topic

**Request Body:** `CreateTopicRequest`

**Response:** `201 Created` → `Topic`

**Errors:**
- `400` - Validation error
- `401` - Unauthorized
- `404` - Deck not found

---

#### `GET /topics/deck/{deck_id}` 🔒
Get topics in a deck with pagination and sorting

**Path Parameters:**
- `deck_id` (string, UUID) - Deck ID

**Query Parameters:**

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `page` | integer | 1 | No | Page number (1-based, minimum: 1) |
| `page_size` | integer | 25 | No | Items per page (minimum: 1, maximum: 100) |
| `sort_by` | string | `"name"` | No | Field to sort by (see sortable fields below) |
| `sort_order` | string | `"asc"` | No | Sort direction: `"asc"` or `"desc"` |

**Sortable Fields:**

| Field | Description | Data Type |
|-------|-------------|----------|
| `name` | Topic name (alphabetical) | string |
| `difficulty` | Topic difficulty level | number (1-10) |
| `stability` | Memory stability | number (hours) |
| `next_review` | Next scheduled review date | datetime |
| `last_reviewed` | Last review date | datetime (nullable) |
| `created_at` | Topic creation date | datetime |
| `updated_at` | Last update date | datetime |

**Response:** `200 OK` → `TopicListResponse`

**Errors:**
- `401` - Unauthorized
- `404` - Deck not found
- `422` - Invalid query parameters

**Breaking Change Notice (v2.0):**  
This endpoint previously returned `Topic[]`. It now returns `TopicListResponse` with pagination metadata. Frontend code must be updated:

```typescript
// OLD (before v2.0):
const topics = await response.json(); // Topic[]

// NEW (v2.0+):
const data = await response.json(); // TopicListResponse
const topics = data.items;          // Topic[]
const totalPages = data.total_pages;
const hasMore = data.has_next;
```

**Example Requests:**

```typescript
// Get first page (default: 25 topics, sorted by name ascending)
GET /topics/deck/abc-123?page=1

// Get second page with 50 topics per page
GET /topics/deck/abc-123?page=2&page_size=50

// Sort by difficulty (hardest first)
GET /topics/deck/abc-123?sort_by=difficulty&sort_order=desc

// Sort by next review date (most overdue first)
GET /topics/deck/abc-123?sort_by=next_review&sort_order=asc

// Get page 3, sorted by stability (longest intervals first)
GET /topics/deck/abc-123?page=3&page_size=25&sort_by=stability&sort_order=desc
```

**Example Response:**

```typescript
{
  items: [
    {
      id: "topic-uuid-1",
      deck_id: "deck-uuid",
      name: "Topic A",
      stability: 48.5,
      difficulty: 4.2,
      next_review: "2025-12-28T10:00:00Z",
      last_reviewed: "2025-12-26T10:00:00Z",
      cards: [ /* ... */ ],
      created_at: "2025-12-20T10:00:00Z",
      updated_at: "2025-12-26T10:00:00Z"
    },
    // ... more topics (up to page_size)
  ],
  total: 127,           // Total topics in deck
  page: 1,              // Current page
  page_size: 25,        // Items per page
  total_pages: 6,       // Ceiling(127 / 25) = 6 pages
  has_next: true,       // More pages available
  has_prev: false       // No previous page (page 1)
}
```

---

#### `GET /topics/due` 🔒
Get topics due for review

**Query Parameters:**
- `limit` (integer, optional) - Maximum number of topics to return

**Response:** `200 OK` → `Topic[]`

Topics are ordered by `next_review` (ascending), showing the most overdue first.

**Errors:**
- `401` - Unauthorized

---

#### `GET /topics/{topic_id}` 🔒
Get a specific topic by ID

**Path Parameters:**
- `topic_id` (string, UUID) - Topic ID

**Response:** `200 OK` → `Topic`

**Errors:**
- `401` - Unauthorized
- `404` - Topic not found

---

#### `PATCH /topics/{topic_id}` 🔒
Update a topic

**Path Parameters:**
- `topic_id` (string, UUID) - Topic ID

**Request Body:** `UpdateTopicRequest`

**Response:** `200 OK` → `Topic`

**Errors:**
- `400` - Validation error
- `401` - Unauthorized
- `404` - Topic not found

---

#### `DELETE /topics/{topic_id}` 🔒
Delete a topic and all its embedded cards

**Path Parameters:**
- `topic_id` (string, UUID) - Topic ID

**Response:** `204 No Content`

**Errors:**
- `401` - Unauthorized
- `404` - Topic not found

**Note:** This operation deletes the topic and all its embedded cards in the JSONB array.

---

#### `POST /topics/{topic_id}/cards` 🔒
Add a new card to a topic's cards array

**Path Parameters:**
- `topic_id` (string, UUID) - Topic ID

**Request Body:** `CreateCardRequest` (QA Hint or Multiple Choice)

**Response:** `201 Created` → `Topic` (with updated cards array)

**Errors:**
- `400` - Validation error (invalid card_type, correct_index out of bounds, or topic already has 25 cards)
- `401` - Unauthorized
- `404` - Topic not found

**Note:** 
- Maximum 25 cards per topic
- All text fields support Markdown formatting
- Returns the full updated topic with the new card added

**Example Request (QA Hint Card):**
```typescript
POST /topics/abc-123/cards
Body: {
  card_type: "qa_hint",
  question: "What is the capital of France?",
  answer: "Paris",
  hint: "City of lights",
  intrinsic_weight: 1.5
}
```

**Example Request (Multiple Choice Card):**
```typescript
POST /topics/abc-123/cards
Body: {
  card_type: "multiple_choice",
  question: "Which is a programming language?",
  choices: ["Python", "HTML", "CSS"],
  correct_index: 0,
  explanation: "Python is a programming language. HTML and CSS are markup/styling languages.",
  intrinsic_weight: 1.0
}
```

---

#### `POST /topics/{topic_id}/cards/batch` 🔒
Add multiple cards to a topic's cards array in batch mode

**Path Parameters:**
- `topic_id` (string, UUID) - Topic ID

**Request Body:** `CardCreateBatch`

```typescript
interface CardCreateBatch {
  cards: (CreateQAHintCardRequest | CreateMultipleChoiceCardRequest)[];  // 1-25 cards
  mode?: 'append' | 'replace';  // Default: 'append'
}
```

**Response:** `201 Created` → `Topic` (with updated cards array)

**Errors:**
- `400` - Validation error (card validation failed, would exceed 25 card limit, or invalid card data with index context)
- `401` - Unauthorized
- `404` - Topic not found

**Behavior:**
- **Append mode** (default): Adds cards to existing cards array
  - Validates: `existing_cards + new_cards <= 25`
  - Error example: "Cannot add 5 cards. Topic has 22 cards, would exceed limit of 25 (total would be 27)."
- **Replace mode**: Clears existing cards and adds new ones
  - Validates: `new_cards <= 25`
  - Error example: "Cannot add 30 cards. Maximum 25 cards per topic."
- **All-or-nothing**: If any card fails validation, the entire batch is rejected
- **Error context**: Validation errors include card index, e.g., "Card at index 2: correct_index must be between 0 and 2"

**Example Request (Append Mode - Mixed Card Types):**
```typescript
POST /topics/abc-123/cards/batch
Body: {
  mode: "append",
  cards: [
    {
      card_type: "qa_hint",
      question: "What is the capital of France?",
      answer: "Paris",
      hint: "City of lights",
      intrinsic_weight: 1.5
    },
    {
      card_type: "multiple_choice",
      question: "Which is a programming language?",
      choices: ["Python", "HTML", "CSS"],
      correct_index: 0,
      explanation: "Python is a programming language, while HTML and CSS are not.",
      intrinsic_weight: 1.0
    },
    {
      card_type: "qa_hint",
      question: "What is 2+2?",
      answer: "4",
      intrinsic_weight: 0.5
    }
  ]
}
```

**Example Request (Replace Mode):**
```typescript
POST /topics/abc-123/cards/batch
Body: {
  mode: "replace",
  cards: [
    {
      card_type: "qa_hint",
      question: "New question 1?",
      answer: "New answer 1"
    },
    {
      card_type: "qa_hint",
      question: "New question 2?",
      answer: "New answer 2"
    }
  ]
}
```

**Example Response:**
```typescript
{
  id: "topic-uuid",
  deck_id: "deck-uuid",
  name: "Topic Name",
  stability: 24.0,
  difficulty: 5.0,
  next_review: "2025-12-26T10:00:00Z",
  last_reviewed: null,
  cards: [
    // All cards in the topic (existing + new in append mode, or only new in replace mode)
    {
      card_type: "qa_hint",
      intrinsic_weight: 1.5,
      card_data: {
        question: "What is the capital of France?",
        answer: "Paris",
        hint: "City of lights"
      }
    }
    // ... more cards
  ],
  created_at: "2025-12-25T10:00:00Z",
  updated_at: "2025-12-25T10:30:00Z"
}
```

**Example Error Response (Card Validation):**
```typescript
{
  detail: "Card at index 2: correct_index must be between 0 and 2"
}
```

**Example Error Response (Card Limit):**
```typescript
{
  detail: "Cannot add 5 cards. Topic has 22 cards, would exceed limit of 25 (total would be 27)."
}
```

**Notes:**
- Maximum 25 cards per batch request
- All text fields support Markdown formatting
- Returns the full updated topic with all cards
- Frontend should confirm with user before using replace mode to prevent accidental data loss
- Use this endpoint for efficient bulk card creation (e.g., importing flashcards, AI-generated cards)

---

#### `GET /topics/{topic_id}/cards` 🔒
Get all cards from a topic's cards array

**Path Parameters:**
- `topic_id` (string, UUID) - Topic ID

**Response:** `200 OK` → `CardItem[]`

**Errors:**
- `401` - Unauthorized
- `404` - Topic not found

**Note:** Returns the cards array with indices 0-24 (max 25 cards)

---

#### `PATCH /topics/{topic_id}/cards/{index}` 🔒
Update a card at a specific index in the topic's cards array

**Path Parameters:**
- `topic_id` (string, UUID) - Topic ID
- `index` (integer) - Card index in the array (0-24)

**Request Body:** `UpdateCardRequest`

**Response:** `200 OK` → `Topic` (with updated cards array)

**Errors:**
- `400` - Validation error (invalid index, correct_index out of bounds)
- `401` - Unauthorized
- `404` - Topic not found or card index out of range

**Note:** 
- Can update intrinsic_weight and card content fields
- For QA cards: can update question, answer, hint
- For Multiple Choice cards: can update question, choices, correct_index
- Returns the full updated topic

**Example Request:**
```typescript
PATCH /topics/abc-123/cards/0
Body: {
  intrinsic_weight: 2.0,
  question: "Updated question text"
}
```

---

#### `DELETE /topics/{topic_id}/cards/{index}` 🔒
Delete a card at a specific index from the topic's cards array

**Path Parameters:**
- `topic_id` (string, UUID) - Topic ID
- `index` (integer) - Card index in the array (0-24)

**Response:** `200 OK` → `Topic` (with updated cards array)

**Errors:**
- `401` - Unauthorized
- `404` - Topic not found or card index out of range

**Note:** 
- Removes the card from the array
- Returns the full updated topic with remaining cards
- Subsequent cards shift down in index

---

### Review

#### `GET /review/decks/{deck_id}/cards` 🔒
Get up to 100 due cards for review from a deck

**Path Parameters:**
- `deck_id` (string, UUID) - Deck ID

**Response:** `200 OK` → `DeckReviewResponse`

**Algorithm:** 
1. Queries topics with `next_review <= NOW()` in the deck (single query with embedded cards)
2. Orders by `next_review` ascending (most overdue first)
3. Limits to 100 topics
4. Samples one card per topic using weighted sampling by `intrinsic_weight`
5. Returns cards with `topic_id` and `card_index` for tracking

**Errors:**
- `401` - Unauthorized
- `404` - Deck not found
- `500` - Internal error

**Notes:** 
- Cards are fetched from the topics.cards JSONB array (efficient single query)
- All card data is exposed including answers, hints, and correct_index
- Frontend is responsible for hiding/showing answers appropriately
- Each card includes `topic_id` and `card_index` for review submission
- If 100 cards are reviewed and more remain due, send another request

**Example Response:**
```typescript
{
  cards: [
    {
      topic_id: "topic-uuid-1",
      card_index: 2,
      card_type: "qa_hint",
      intrinsic_weight: 1.5,
      card_data: {
        question: "What is...?",
        answer: "It is...",
        hint: "Think about..."
      }
    },
    {
      topic_id: "topic-uuid-2",
      card_index: 0,
      card_type: "multiple_choice",
      intrinsic_weight: 1.0,
      card_data: {
        question: "Which one...?",
        choices: ["Option A", "Option B", "Option C"],
        correct_index: 1,
        explanation: "Option B is correct because..."
      }
    }
  ],
  total_due: 45,
  deck_id: "deck-uuid"
}
```

---

#### `GET /review/decks/{deck_id}/practice` 🔒
Get up to 100 random cards from a deck for practice

**Path Parameters:**
- `deck_id` (string, UUID) - Deck ID

**Response:** `200 OK` → `DeckReviewResponse`

**Algorithm:** 
1. Queries all topics in the deck (no date filtering)
2. Randomly shuffles topics
3. Takes up to 100 topics (or all if fewer)
4. Samples one card per topic using weighted sampling by `intrinsic_weight`
5. Returns cards with `topic_id` and `card_index`

**Errors:**
- `401` - Unauthorized
- `404` - Deck not found
- `500` - Internal error

**Notes:** 
- Returns random cards regardless of SRS scheduling (for practice, not review)
- Does not filter by `next_review` date - includes all topics
- Random order (not ordered by due date)
- All card data is exposed including answers, hints, and correct_index
- Frontend is responsible for hiding/showing answers appropriately
- Returns as many cards as available (up to 100)
- Does **not** affect SRS parameters or scheduling

**Example Response:**
```typescript
{
  cards: [
    {
      topic_id: "topic-uuid-3",
      card_index: 1,
      card_type: "multiple_choice",
      intrinsic_weight: 1.0,
      card_data: {
        question: "Which one...?",
        choices: ["Option A", "Option B", "Option C"],
        correct_index: 2,
        explanation: "Option C is correct because..."
      }
    },
    {
      topic_id: "topic-uuid-7",
      card_index: 0,
      card_type: "qa_hint",
      intrinsic_weight: 1.5,
      card_data: {
        question: "What is...?",
        answer: "It is...",
        hint: "Think about..."
      }
    }
    // ... more cards in random order
  ],
  total_due: 45,  // Number of cards returned
  deck_id: "deck-uuid"
}
```

---

#### `POST /review/topics/{topic_id}/cards/{index}/submit` 🔒
Submit review for a specific card and update its parent topic

**Path Parameters:**
- `topic_id` (string, UUID) - Topic ID
- `index` (integer) - Card index in the topic's cards array (0-24)

**Request Body:** `ReviewSubmission`

**Response:** `200 OK` → `ReviewResponse`

**Errors:**
- `400` - Validation error (invalid base_score or card index out of range)
- `401` - Unauthorized
- `404` - Topic not found or card index invalid
- `500` - Failed to update topic

**SRS Updates:**
- Retrieves the card's `intrinsic_weight` from `topic.cards[index]`
- Updates the topic's SRS parameters:
  - **Stability**: Memory retention time (2.4 - 8760 hours)
  - **Difficulty**: Topic difficulty (1 - 10)
  - **Next Review**: Scheduled review datetime
  - **Last Reviewed**: Current timestamp

**Note:** Each card review updates its parent topic's SRS parameters based on the card's intrinsic weight and the user's base score.

**Example Request:**
```typescript
POST /review/topics/topic-uuid-1/cards/2/submit
Body: { base_score: 2 }
```

**Example Response:**
```typescript
{
  topic_id: "topic-uuid-1",
  card_index: 2,
  new_stability: 48.5,
  new_difficulty: 4.8,
  next_review: "2025-12-26T12:30:00Z",
  message: "Review submitted successfully"
}
```

---

### Admin

#### `POST /admin/users/{user_id}/role` 🔒 (Admin Only)
Update a user's role

**Path Parameters:**
- `user_id` (string, UUID) - Target user ID

**Request Body:** `UpdateUserRoleRequest`

**Response:** `200 OK` → `UpdateUserRoleResponse`

**Example Request:**
```json
{
  "role": "pro"
}
```

**Example Response:**
```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "role": "pro",
  "message": "Role updated to 'pro' successfully. User must re-login for changes to take effect."
}
```

**Role Types:**
- `user` - Default role (free tier, must provide own API keys for AI generation)
- `pro` - Premium user (can use server-side AI API keys)
- `admin` - Administrator (full access + can use server-side AI API keys)

**Errors:**
- `400` - Invalid role value
- `401` - Unauthorized
- `403` - Forbidden (not admin)
- `404` - User not found
- `500` - Failed to update role

**Important Notes:**
- Only admin users can update roles
- Role is stored in Supabase auth `user_metadata.role`
- Users must re-login (refresh JWT token) for role changes to take effect
- Role changes are immediate in the database but require token refresh for API authorization

---

#### `GET /admin/users` 🔒 (Admin Only)
List all users with pagination, filtering, and search

**Query Parameters:**

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `page` | integer | 1 | No | Page number (1-based, minimum: 1) |
| `page_size` | integer | 25 | No | Items per page (minimum: 1, maximum: 100) |
| `sort_by` | string | `"created_at"` | No | Field to sort by (see sortable fields below) |
| `sort_order` | string | `"desc"` | No | Sort direction: `"asc"` or `"desc"` |
| `role` | string | null | No | Filter by role: `"user"`, `"pro"`, or `"admin"` |
| `search` | string | null | No | Search in email or username (case-insensitive substring) |

**Sortable Fields:**

| Field | Description | Data Type |
|-------|-------------|----------|
| `email` | User email address (alphabetical) | string |
| `username` | Display name (alphabetical) | string |
| `role` | User role | string |
| `created_at` | Account creation date | datetime |

**Response:** `200 OK` → `UserListResponse`

**Errors:**
- `401` - Unauthorized
- `403` - Forbidden (not admin)
- `422` - Invalid query parameters
- `500` - Failed to list users

**Example Requests:**

```typescript
// Get first page (default: 25 users, sorted by created_at descending)
GET /admin/users?page=1

// Get second page with 50 users per page
GET /admin/users?page=2&page_size=50

// Sort by email (alphabetical)
GET /admin/users?sort_by=email&sort_order=asc

// Filter by role (only pro users)
GET /admin/users?role=pro

// Search for users with "john" in email or username
GET /admin/users?search=john

// Combine: search for admins with "smith" in email/username, sorted by username
GET /admin/users?role=admin&search=smith&sort_by=username&sort_order=asc
```

**Example Response:**

```typescript
{
  items: [
    {
      id: "123e4567-e89b-12d3-a456-426614174000",
      email: "john.doe@example.com",
      username: "John Doe",
      avatar: "https://avatar.iran.liara.run/public/42",
      role: "pro",
      created_at: "2025-12-01T10:30:00Z"
    },
    {
      id: "987fcdeb-51a2-43f7-9c8d-6e5a4b3c2d1e",
      email: "jane.smith@example.com",
      username: "Jane Smith",
      avatar: null,
      role: "user",
      created_at: "2025-12-15T14:20:00Z"
    }
  ],
  total: 2,
  page: 1,
  page_size: 25,
  total_pages: 1,
  has_next: false,
  has_prev: false
}
```

**Notes:**
- Only admin users can list all users
- Username defaults to "User" if not set during signup
- Avatar can be null if not set
- Role defaults to "user" if not set in user_metadata
- Search is case-insensitive and matches substrings in both email and username fields
- Total count reflects the number of users after filtering (not all users in the system)
- Results are fetched from Supabase auth system, not from a user_profiles table

---

### AI Generation

AI-powered flashcard generation using various LLM providers.

#### Environment Variables (Backend)

For server-side API key fallback (pro/admin users), configure these on the backend:

```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...
XAI_API_KEY=xai-...
```

---

#### `GET /ai/providers` 🔒
Get available AI providers and models

**Response:** `200 OK` → `AIProvidersResponse`

**Example Response:**
```typescript
{
  providers: [
    {
      id: "openai",
      display_name: "OpenAI",
      models: [
        { id: "gpt-4o", name: "GPT-4o" },
        { id: "gpt-4o-mini", name: "GPT-4o Mini" }
      ]
    },
    {
      id: "anthropic",
      display_name: "Anthropic",
      models: [
        { id: "claude-3-5-sonnet-latest", name: "Claude 3.5 Sonnet" }
      ]
    }
    // ... more providers
  ],
  default_provider: "openai",
  default_model: "gpt-4o-mini"
}
```

**Errors:**
- `401` - Unauthorized

---

#### `POST /ai/generate-cards` 🔒
Generate flashcards using AI

**Request Body:** `GenerateCardsRequest`

**API Key Behavior:**
- If `api_key` is provided (non-empty string), it will be used for the AI request.
- If `api_key` is empty/omitted and user role is `'pro'` or `'admin'`, the server-side API key from environment variables is used.
- If `api_key` is empty/omitted and user role is `'user'`, returns `403 Forbidden`.

**Example Request:**
```typescript
POST /ai/generate-cards
Body: {
  deck_prompt: "You are a helpful assistant creating flashcards for learning TypeScript...",
  topic_name: "TypeScript Generics",
  provider: "openai",
  model: "gpt-4o-mini",
  api_key: "sk-..." // Optional for pro/admin users
}
```

**Response:** `201 Created` → `GenerateCardsResponse`

**Example Response:**
```typescript
{
  cards: [
    {
      card_type: "qa_hint",
      question: "What is a generic type in TypeScript?",
      answer: "A generic type is a type that can work with multiple types...",
      hint: "Think of it as a type placeholder"
    },
    {
      card_type: "multiple_choice",
      question: "Which syntax declares a generic function?",
      choices: [
        "function fn<T>(arg: T): T",
        "function fn(arg: T): T",
        "function fn<>(arg): T",
        "generic function fn(arg)"
      ],
      correct_index: 0,
      explanation: "The angle brackets <T> declare a type parameter..."
    }
  ]
}
```

**Errors:**
- `400` - Validation error, invalid provider/model, or AI provider API error
- `401` - Unauthorized
- `403` - API key required (user role is 'user' and no api_key provided)
- `500` - Server-side API key not configured, or AI response parsing error

**Supported Providers:**

| Provider | ID | Example Models |
|----------|-----|----------------|
| OpenAI | `openai` | `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo` |
| Anthropic | `anthropic` | `claude-3-5-sonnet-latest`, `claude-3-5-haiku-latest` |
| Google | `google` | `gemini-2.0-flash-exp`, `gemini-1.5-pro` |
| xAI | `xai` | `grok-2-latest`, `grok-beta` |

---

## SRS Algorithm & Review Workflow

### Core Parameters

#### Stability (S)
Memory retention time in **hours**
- **Range:** 2.4 hours (min) to 8760 hours / 365 days (max)
- **Default:** 24.0 hours
- Represents how long information stays in memory

#### Difficulty (D)
Topic difficulty rating
- **Range:** 1.0 (easiest) to 10.0 (hardest)
- **Default:** 5.0
- Affects interval calculation

#### Intrinsic Weight (W)
Card importance multiplier (dynamically updated after each review)
- **Range:** 0.5 to 2.0
- **Default:** 1.0
- Amplifies review performance impact
- **Updated based on performance:** Cards rated "Again" increase in weight (need more attention), cards rated "Easy" decrease (well-learned)

#### Base Score (B)
Review rating from user
- `0` = **Again** (failed recall)
- `1` = **Hard** (difficult recall)
- `2` = **Good** (normal recall)
- `3` = **Easy** (effortless recall)

---

### Stability Update Formula

When a user submits a review:

```
If base_score == 0 (Again):
    S_new = max(2.4, S_current × 0.5)
Else:
    effective_score = base_score × intrinsic_weight
    growth_factor = 1 + (effective_score × 0.15)
    S_new = S_current × growth_factor

# Apply bounds: [2.4, 8760] hours
```

**Example:**
- Current stability: 48 hours
- Base score: 2 (Good)
- Intrinsic weight: 1.5 (important card)
- Effective score: 2 × 1.5 = 3.0
- Growth factor: 1 + (3.0 × 0.15) = 1.45
- **New stability: 48 × 1.45 = 69.6 hours**

---

### Difficulty Update Formula

```
effective_score = base_score × intrinsic_weight
difficulty_delta = (effective_score - 2.0) × 0.3
D_new = D_current - difficulty_delta

# Apply bounds: [1.0, 10.0]
```

**Example:**
- Current difficulty: 5.0
- Base score: 3 (Easy)
- Intrinsic weight: 1.0
- Effective score: 3 × 1.0 = 3.0
- Difficulty delta: (3.0 - 2.0) × 0.3 = 0.3
- **New difficulty: 5.0 - 0.3 = 4.7** (easier)

---

### Intrinsic Weight Update Formula

The card's `intrinsic_weight` is dynamically updated after each review based on performance. Cards that are difficult to remember become more important (higher weight), while well-learned cards become less important (lower weight).

```
WEIGHT_MULTIPLIERS = {
    0: 1.05,  # Again - increase weight (card needs more attention)
    1: 1.01,  # Hard - slight increase
    2: 0.99,  # Good - slight decrease
    3: 0.95   # Easy - decrease weight (card is well-learned)
}

W_new = W_current × WEIGHT_MULTIPLIERS[base_score]

# Apply bounds: [0.5, 2.0]
```

**Example 1 (Again):**
- Current weight: 1.0
- Base score: 0 (Again)
- Multiplier: 1.05
- **New weight: 1.0 × 1.05 = 1.05**

**Example 2 (Easy, multiple reviews):**
- Current weight: 1.5
- Base score: 3 (Easy)
- Multiplier: 0.95
- **New weight: 1.5 × 0.95 = 1.425**

**Convergence:**
- A card starting at 1.0 requires ~14 consecutive "Again" ratings to reach the max of 2.0
- A card starting at 1.0 requires ~14 consecutive "Easy" ratings to reach the min of 0.5

---

### Next Review Calculation

```
difficulty_modifier = 1 + (D - 5) × 0.12
interval_hours = stability × difficulty_modifier
next_review = now + interval_hours
```

**Example:**
- Stability: 72 hours
- Difficulty: 6.0
- Difficulty modifier: 1 + (6 - 5) × 0.12 = 1.12
- Interval: 72 × 1.12 = 80.64 hours
- **Next review: now + 80.64 hours**

---

### Weighted Card Sampling

When requesting a review card, the system uses **stochastic weighted sampling**:

```typescript
// Cards with higher intrinsic weights have proportionally 
// higher probability of being selected
weights = [card.intrinsic_weight for card in cards]
selected_card = random.choices(cards, weights=weights, k=1)[0]
```

**Impact:**
- Card with weight 2.0 is **twice as likely** to appear as one with weight 1.0
- Card with weight 0.5 is **half as likely** to appear

---

### Review Workflow

**Step-by-step process for implementing deck-level reviews:**

1. **Get due cards from a deck**
   ```typescript
   GET /review/decks/{deck_id}/cards
   
   // Returns up to 100 cards (one per due topic), most overdue first
   // Cards are fetched from topics.cards JSONB array (single efficient query)
   {
     cards: [
       {
         topic_id: "topic-uuid-1",
         card_index: 2,                // Index in topic's cards array
         card_type: "qa_hint",
         intrinsic_weight: 1.5,
         card_data: {
           question: "What is...?",
           answer: "It is...",         // Full answer exposed
           hint: "Think about..."
         }
       },
       {
         topic_id: "topic-uuid-2",
         card_index: 0,
         card_type: "multiple_choice",
         intrinsic_weight: 1.0,
         card_data: {
           question: "Which one...?",
           choices: ["A", "B", "C"],
           correct_index: 1,
           explanation: "B is the correct answer."
         }
       }
       // ... more cards
     ],
     total_due: 100,
     deck_id: "deck-uuid"
   }
   ```

2. **Display cards to user one by one**
   - Show the `card_data.question` field
   - For QA cards: Let user think, optionally show `card_data.hint`, then reveal `card_data.answer`
   - For Multiple Choice: Show `card_data.choices`, user selects one, then reveal `card_data.correct_index` and `card_data.explanation`
   - Frontend manages hiding/showing answers appropriately

3. **User rates their recall**
   - Ask: "How well did you remember this?"
   - Options: Again (0), Hard (1), Good (2), Easy (3)

4. **Submit review for each card using topic_id and card_index**
   ```typescript
   POST /review/topics/{topic_id}/cards/{card_index}/submit
   Body: { base_score: 2 }
   
   // Example: POST /review/topics/topic-uuid-1/cards/2/submit
   
   // Response includes updated SRS parameters for the topic:
   {
     topic_id: "topic-uuid-1",
     card_index: 2,
     new_stability: 69.6,
     new_difficulty: 4.8,
     next_review: "2025-12-24T10:30:00Z",
     message: "Review submitted successfully"
   }
   ```

5. **Show feedback**
   - Display next review time
   - Optionally show updated stability/difficulty
   - Track which cards have been reviewed in the session

6. **Continue with remaining cards**
   - Process all cards from the batch
   - If all 100 cards are reviewed and `total_due > 100`, send another request to get the next batch

**Notes:**
- Reviews are done at the **deck level** (not individual topics)
- Each card review updates its **parent topic's** SRS parameters
- The card's `intrinsic_weight` amplifies the effect of the review score
- Frontend tracks which `topic_id + card_index` pairs have been submitted to avoid duplicates
- Multiple requests can be made if more than 100 topics are due
- Cards are efficiently fetched from the topics.cards JSONB array in a single query

---

## Database Schema

### Overview

The system uses **three main tables** with PostgreSQL's JSONB support for embedded cards:

### Tables

#### `decks`
```sql
CREATE TABLE decks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL CHECK (char_length(name) >= 1),
  prompt TEXT NOT NULL,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### `topics`
```sql
CREATE TABLE topics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deck_id UUID NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL CHECK (char_length(name) >= 1),
  cards JSONB NOT NULL DEFAULT '[]'::jsonb,  -- Embedded cards array (max 25)
  stability NUMERIC(10, 2) NOT NULL DEFAULT 24.0 CHECK (stability > 0),
  difficulty NUMERIC(3, 1) NOT NULL DEFAULT 5.0 CHECK (difficulty >= 1 AND difficulty <= 10),
  next_review TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_reviewed TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT max_cards_per_topic CHECK (jsonb_array_length(cards) <= 25)
);
```

**Cards JSONB Structure:**
```typescript
// Each element in the cards array:
{
  card_type: 'qa_hint' | 'multiple_choice',
  intrinsic_weight: number,  // 0.5-2.0
  card_data: {
    // For qa_hint:
    question: string,
    answer: string,
    hint: string
    
    // For multiple_choice:
    question: string,
    choices: string[],
    correct_index: number
  }
}
```

#### `user_profiles`
```sql
CREATE TABLE user_profiles (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  username VARCHAR(50) UNIQUE NOT NULL,
  avatar TEXT,
  role VARCHAR(20) DEFAULT 'user',
  ai_prompts JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Key Architecture Points

1. **No Separate Cards Table**: Cards are embedded in topics as a JSONB array
2. **Maximum 25 Cards Per Topic**: Enforced by database constraint
3. **No Card IDs or Timestamps**: Cards are referenced by array index (0-24)
4. **Single Query Performance**: Fetching topics includes all embedded cards
5. **Atomic Updates**: Card operations update the entire cards array atomically
6. **Row-Level Security**: All tables use RLS to enforce user data isolation

---

## Integration Notes

### Authentication Flow

1. **User signs up/logs in with Supabase**
   ```typescript
   const { data, error } = await supabase.auth.signInWithPassword({
     email: 'user@example.com',
     password: 'password'
   });
   
   const token = data.session?.access_token;
   ```

2. **Include token in all API requests**
   ```typescript
   const headers = {
     'Authorization': `Bearer ${token}`,
     'Content-Type': 'application/json'
   };
   ```

3. **Handle token refresh**
   ```typescript
   supabase.auth.onAuthStateChange((event, session) => {
     if (session) {
       // Update token in your API client
       apiClient.setToken(session.access_token);
     }
   });
   ```

---

### User Roles and Permissions

**Role System:**
User roles are managed through Supabase auth metadata and included in JWT tokens:

- **user** (default): Free tier, must provide own API keys for AI generation
- **pro**: Premium tier, can use server-side AI API keys
- **admin**: Full access including role management and server-side AI keys

**Role Storage:**
- Roles are stored in `auth.users.raw_app_meta_data.role`
- Automatically set to `'user'` on signup via database trigger
- Included in JWT `user_metadata.role` for fast authorization
- Updated via admin endpoint using Supabase Admin SDK

**Username and Avatar:**
- Stored in `auth.users.raw_user_meta_data`
- Set during signup or updated via `supabase.auth.updateUser()`
- Username defaults to "User" if not provided
- Avatar defaults to random avatar from https://avatar.iran.liara.run/public/1-100

---

### Error Handling

All errors follow a consistent structure:

```typescript
interface ApiError {
  detail: string;
}
```

**Common status codes:**
- `200` - Success (GET, PATCH)
- `201` - Created (POST)
- `204` - No Content (DELETE)
- `400` - Bad Request (validation errors)
- `401` - Unauthorized (missing/invalid token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `409` - Conflict (e.g., duplicate username)
- `500` - Internal Server Error

**Example error handling:**
```typescript
try {
  const response = await fetch(url, options);
  
  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail);
  }
  
  return await response.json();
} catch (error) {
  console.error('API Error:', error.message);
}
```

---

### Markdown Support

All card text fields support **Markdown formatting**:
- `question`, `answer`, `hint` (QA cards)
- `question`, `choices[]` (Multiple Choice cards)

**Supported Markdown:**
- **Bold**: `**text**`
- *Italic*: `*text*`
- Code: `` `code` ``
- Code blocks: ` ```language ... ``` `
- Lists, links, images, etc.

**Frontend rendering:**
Use a Markdown renderer library (e.g., `react-markdown`, `marked`) to display card content.

```typescript
import ReactMarkdown from 'react-markdown';

<ReactMarkdown>{card.question}</ReactMarkdown>
```

---

### Row-Level Security (RLS)

The API uses **Supabase Row-Level Security** for access control:

- Users can **only access their own data**
- Security is enforced at the **database level** (not just API level)
- No additional authorization checks needed in frontend
- If a user tries to access another user's data, they receive a `404` (not `403`)

**What this means:**
- You don't need to filter data by user_id in your queries
- The API automatically returns only the authenticated user's data
- Trust the API's authorization - if it returns data, the user owns it

---

### Validation Rules Summary

**Deck:**
- `name`: 1-255 characters, required
- `prompt`: Required

**Topic:**
- `name`: 1-255 characters, required
- `cards`: Maximum 25 cards per topic
- `stability`: > 0, default: 24.0
- `difficulty`: 1-10, default: 5.0

**Card:**
- `question`: Minimum 1 character, required
- `answer`: Minimum 1 character, required (QA cards)
- `hint`: Optional, default: '' (QA cards)
- `choices`: Minimum 2 items, required (Multiple Choice)
- `correct_index`: >= 0, must be valid index into choices array
- `explanation`: Optional, default: '', shown after user answers (Multiple Choice only)
- `intrinsic_weight`: 0.5-2.0, default: 1.0

**Profile:**
- `username`: 3-50 characters, alphanumeric + underscore + hyphen, required
- `avatar`: Must be valid HTTP/HTTPS URL

---

## Quick Reference

### Most Common Operations

**Create a deck:**
```
POST /decks/
Body: { name: "My Deck", prompt: "..." }
```

**Create a topic:**
```
POST /topics/
Body: { deck_id: "...", name: "My Topic" }
```

**Add a QA card to a topic:**
```
POST /topics/{topic_id}/cards
Body: {
  card_type: "qa_hint",
  question: "What is...?",
  answer: "It is...",
  hint: "Think about...",
  intrinsic_weight: 1.5
}
```

**Add a Multiple Choice card to a topic:**
```
POST /topics/{topic_id}/cards
Body: {
  card_type: "multiple_choice",
  question: "Which one...?",
  choices: ["Option A", "Option B", "Option C"],
  correct_index: 1,
  explanation: "Option B is correct because...",
  intrinsic_weight: 1.0
}
```

**Add cards in batch:**
```
POST /topics/{topic_id}/cards/batch
Body: {
  mode: "append",  // or "replace"
  cards: [
    { card_type: "qa_hint", question: "Q1?", answer: "A1" },
    { card_type: "multiple_choice", question: "Q2?", choices: ["A", "B"], correct_index: 0 }
  ]
}
// Returns full Topic with all cards
```

**Get all cards in a topic:**
```
GET /topics/{topic_id}/cards
// Returns CardItem[] array
```

**Update a card in a topic:**
```
PATCH /topics/{topic_id}/cards/{index}
Body: { intrinsic_weight: 2.0 }
```

**Delete a card from a topic:**
```
DELETE /topics/{topic_id}/cards/{index}
// Returns updated topic with card removed
```

**Get topics in a deck (paginated):**
```
GET /topics/deck/{deck_id}
// Default: page 1, 25 items, sorted by name ascending
// Returns TopicListResponse with items, total, page, page_size, total_pages, has_next, has_prev

// Examples:
GET /topics/deck/{deck_id}?page=2&page_size=50
GET /topics/deck/{deck_id}?sort_by=difficulty&sort_order=desc
GET /topics/deck/{deck_id}?sort_by=next_review&sort_order=asc&page=1&page_size=25
```

**Get due cards for a deck:**
```
GET /review/decks/{deck_id}/cards
// Returns up to 100 cards from due topics with topic_id and card_index
```

**Get random practice cards from a deck:**
```
GET /review/decks/{deck_id}/practice
// Returns up to 100 random cards for practice (no date filtering, random order)
// Does not affect SRS scheduling
```

**Submit a card review:**
```
POST /review/topics/{topic_id}/cards/{index}/submit
Body: { base_score: 2 }
// Updates the topic's SRS parameters
```

---

**Last Updated:** December 31, 2025
