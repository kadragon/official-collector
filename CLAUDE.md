# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Korean official document automation system built with Python 3.12+ that uses RPA (Robotic Process Automation) to classify and process official documents automatically. The system integrates with Supabase for vector storage and OpenAI for embeddings to provide intelligent document matching and recommendations.

## Key Commands

### Running the Application

```bash
uv run ./src/main.py
```

### Data Management Operations

#### Deleting Stored Data

```bash
# Run deletion interface through main application
uv run ./src/main.py --delete

# Or run standalone deletion script
uv run ./src/delete_data.py
```

The deletion interface provides options to:
- View and delete individual task cards or reception documents
- Delete items by title search
- Bulk delete multiple selected items
- Delete all stored data (with confirmation prompts)

### Installing Dependencies

```bash
uv install
```

### Code Quality Tools

#### Running Pylint

```bash
# Check all source code for quality issues
uv run pylint src/

# Check specific file or directory
uv run pylint src/main.py
uv run pylint src/services/

# Generate detailed report with score
uv run pylint src/ --score=yes

# Fix only specific message types
uv run pylint src/ --disable=trailing-whitespace,line-too-long
```

The project includes a `.pylintrc` configuration file with Korean-friendly settings:
- Supports Korean variable names and comments
- Configured for RPA automation context
- Minimum score threshold: 7.0/10
- Customized rules for the project's specific needs

## Environment Setup

Required environment variables in `.env`:

```
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
SUPABASE_URL=YOUR_SUPABASE_URL
SUPABASE_KEY=YOUR_SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY=YOUR_SUPABASE_SERVICE_ROLE_KEY
```

## Core Architecture

### Main Components

1. **Main Entry Point** (`src/main.py`): Orchestrates the document processing workflow, handling both reception documents (접수) and regular documents (전자결재)

2. **RPA Controller** (`src/services/official_collector.py`): Uses pywinauto to automate Windows applications for document processing, including approval workflows and document classification

3. **AI-Powered Services**:

   - `ReceptionService`: Handles incoming document assignment using vector similarity
   - `TaskCardService`: Matches documents to task cards using embeddings
   - `SupabaseService`: Manages vector storage and similarity search

4. **User Interaction** (`src/services/dialog_service.py`): Provides CLI-based user selection when automated matching isn't confident enough

### Data Flow

1. System monitors for new documents in Windows applications
2. For reception documents: finds appropriate handler and approval chain
3. For regular documents: matches to existing task cards or prompts user selection
4. Uses vector embeddings for intelligent matching with learning capability
5. Stores successful matches for future automatic processing

### Technology Stack

- **RPA**: pywinauto for Windows automation
- **AI/ML**: OpenAI embeddings via langchain
- **Database**: Supabase with pgvector for semantic search
- **UI**: Command-line interface for user decisions
- **Configuration**: python-dotenv for environment management

## Data Management

- `data/base_data.json`: Contains predefined lists for receptions, shares, and task cards
- `data/backup/`: Stores historical processing data with timestamps
- Local embedding cache in `.cache/` directory

## Code Structure Notes

- Services follow dependency injection pattern
- Korean comments and variable names are used throughout
- Error handling focuses on graceful degradation with user fallback
- Vector embeddings use consistent UUID generation for deduplication
