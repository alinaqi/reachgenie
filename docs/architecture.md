# Architectural Overview

## System Architecture

```mermaid
graph TB
    subgraph Frontend
        UI[User Interface]
    end

    subgraph Backend
        API[FastAPI Backend]
        Auth[Authentication Service]
        DB[(Supabase DB)]
        AI[AI Services]
        Email[Email Service]
        Calendar[Calendar Service]
        Tasks[Background Tasks]
    end

    subgraph External Services
        OpenAI[OpenAI GPT-4]
        Perplexity[Perplexity API]
        BlandAI[Bland AI]
        SMTP[SMTP Servers]
        Cronofy[Cronofy Calendar]
    end

    UI --> API
    API --> Auth
    API --> DB
    API --> AI
    API --> Email
    API --> Calendar
    API --> Tasks
    
    AI --> OpenAI
    AI --> Perplexity
    AI --> BlandAI
    Email --> SMTP
    Calendar --> Cronofy
```

## Core Business Flow

```mermaid
graph TD
    A[User] --> B[Create Company]
    B --> C[Add Products/Value Propositions]
    C --> D[Upload Leads]
    D --> E{Campaign Type}
    E --> |Email| F[Email Campaign]
    E --> |Phone| G[Call Campaign]
    
    F --> H[AI Generated Emails]
    F --> I[Email Tracking]
    F --> J[Response Processing]
    F --> K[Auto Follow-ups]
    
    G --> L[AI Call Script]
    G --> M[Automated Calls]
    G --> N[Call Analysis]
    G --> O[Meeting Booking]
    
    subgraph Results
        P[Analytics]
        Q[Meeting Scheduling]
        R[Lead Status Updates]
    end
    
    F --> Results
    G --> Results
```

## Data Model Relationships

```mermaid
erDiagram
    USERS ||--o{ USER_COMPANY_PROFILES : has
    COMPANIES ||--o{ USER_COMPANY_PROFILES : has
    COMPANIES ||--o{ PRODUCTS : contains
    COMPANIES ||--o{ LEADS : manages
    PRODUCTS ||--o{ CAMPAIGNS : has
    CAMPAIGNS ||--o{ CALLS : generates
    CAMPAIGNS ||--o{ EMAIL_LOGS : generates
    EMAIL_LOGS ||--o{ EMAIL_LOG_DETAILS : contains
    LEADS ||--o{ CALLS : receives
    LEADS ||--o{ EMAIL_LOGS : receives

    USERS {
        UUID id
        string email
        string password_hash
        boolean verified
    }
    
    COMPANIES {
        UUID id
        string name
        string industry
        string website
        json voice_agent_settings
        boolean deleted
    }
    
    PRODUCTS {
        UUID id
        UUID company_id
        string product_name
        string description
    }
    
    LEADS {
        UUID id
        UUID company_id
        string name
        string email
        string phone_number
        json company_info
    }
    
    CAMPAIGNS {
        UUID id
        UUID company_id
        UUID product_id
        string name
        string type
        string template
    }
```

## Email Processing Flow

```mermaid
sequenceDiagram
    participant User
    participant System
    participant AI
    participant SMTP
    participant IMAP
    
    User->>System: Create Email Campaign
    System->>AI: Generate Email Content
    AI-->>System: Return Personalized Content
    System->>SMTP: Send Initial Email
    
    loop Email Monitoring
        System->>IMAP: Check for Replies
        IMAP-->>System: Return New Emails
        alt Has Reply
            System->>AI: Generate Response
            AI-->>System: Return AI Response
            System->>SMTP: Send Follow-up
        else No Reply After 2 Days
            System->>AI: Generate Reminder
            AI-->>System: Return Reminder Content
            System->>SMTP: Send Reminder
        end
    end
```

## Call Campaign Flow

```mermaid
sequenceDiagram
    participant User
    participant System
    participant AI
    participant BlandAI
    participant Calendar
    
    User->>System: Create Call Campaign
    System->>AI: Generate Call Script
    AI-->>System: Return Personalized Script
    
    loop For Each Lead
        System->>BlandAI: Initiate Call
        BlandAI-->>System: Call Status Updates
        
        alt Positive Response
            BlandAI->>System: Meeting Request
            System->>Calendar: Check Availability
            Calendar-->>System: Available Slots
            BlandAI->>System: Slot Selected
            System->>Calendar: Book Meeting
        end
        
        BlandAI-->>System: Call Summary & Sentiment
        System->>User: Update Dashboard
    end
```

## Background Tasks

```mermaid
graph TB
    subgraph Cron Jobs
        A[Process Emails]
        B[Send Reminders]
        C[Update Call Stats]
    end
    
    subgraph Tasks
        D[Lead Upload Processing]
        E[Campaign Execution]
        F[Email Response Generation]
    end
    
    subgraph Monitoring
        G[Email Tracking]
        H[Call Status Updates]
        I[Meeting Confirmations]
    end
    
    A --> D
    B --> E
    C --> F
    D --> G
    E --> H
    F --> I
```

## Security Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant Auth
    participant DB
    
    User->>Frontend: Login Request
    Frontend->>API: Auth Request
    API->>Auth: Validate Credentials
    Auth->>DB: Check User
    DB-->>Auth: User Data
    Auth-->>API: JWT Token
    API-->>Frontend: Auth Response
    Frontend-->>User: Login Success
    
    Note over Frontend,API: All subsequent requests include JWT
    
    loop For Each Request
        Frontend->>API: API Request + JWT
        API->>Auth: Validate Token
        Auth-->>API: Token Valid
        API->>DB: Process Request
        DB-->>API: Response
        API-->>Frontend: API Response
    end
```

## Development Environment

```mermaid
graph LR
    subgraph Local Dev
        A[FastAPI Dev Server]
        B[Python venv]
        C[Local DB]
    end
    
    subgraph Testing
        D[Unit Tests]
        E[Integration Tests]
        F[API Tests]
    end
    
    subgraph Production
        G[Render Deploy]
        H[Supabase DB]
        I[Cron Jobs]
    end
    
    A --> D
    A --> E
    A --> F
    D --> G
    E --> G
    F --> G
``` 