# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Korean official document automation system built with Python 3.12+ that uses RPA (Robotic Process Automation) to classify and process official documents automatically. The system integrates with Supabase for database and vector storage and OpenAI for embeddings to provide intelligent document matching and recommendations.

## Key Commands

### Running the Application

```bash
# Standard mode (auto-continue processing)
uv run ./src/main.py

# Interactive mode (user confirmation for each document)
uv run ./src/main.py --interactive
```

### Testing the Integration

Before running the main application, test if Supabase connection is working correctly:

```bash
# Install dev dependencies first
uv sync --group dev

# Run unit tests
pytest tests/unit/ -v

# Run with coverage report
pytest tests/ --cov=src --cov-report=html
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

#### Window Structure Debugging for RPA

For debugging pywinauto automation issues and analyzing window structures, use the unified debug manager:

```bash
# Interactive debugging session (for human use)
uv run -m src.debug.debug_manager

# Or directly run the interactive session
uv run -c "from src.debug import run_interactive_debug; run_interactive_debug()"
```

**Unified Debug Manager Features:**

- **Dual-mode support**: Both interactive (human) and programmatic (AI) interfaces
- **Window structure analysis**: Complete control hierarchy using pywinauto's `print_control_identifiers()`
- **Real-time monitoring**: Track dialog appearances and changes during RPA execution
- **Circulation completion debugging**: Specialized flow for debugging approval processes
- **Automatic connection**: Tries both "접수:" and "전자결재" window patterns
- **Structure export**: Saves window structure snapshots to `./logs/debug/` directory

**Programmatic Interface (for AI/automated debugging):**

```python
from src.debug import (
    create_debug_manager,
    quick_window_analysis,
    monitor_circulation_dialogs
)

# Quick window analysis
debug_info = quick_window_analysis()

# Advanced programmatic debugging
manager = create_debug_manager(interactive=False)
analysis = manager.analyze_current_window()
dialogs = manager.monitor_dialogs(duration=10.0, interval=0.5)
circulation_dialog = manager.find_circulation_completion_dialog(timeout=5.0)

# Monitor circulation dialogs (convenience function)
dialogs = monitor_circulation_dialogs(duration=10.0)
```

**Interactive Interface Options:**
1. Print current window structure
2. Monitor dialog changes with custom duration/interval
3. Debug circulation completion flow
4. Find circulation completion dialogs
5. Exit

**Use this tool when:**
- RPA scripts fail to find expected windows or controls
- Dialog timing issues cause automation failures
- Need to update control selectors after UI changes
- Optimizing wait times and polling intervals
- AI needs to analyze window structure programmatically
- Debugging circulation completion flow timing issues

## Environment Setup

Required environment variables in `.env`:

```
# OpenAI Configuration (for embeddings)
OPENAI_API_KEY=YOUR_OPENAI_API_KEY

# Supabase Configuration (for database and vector storage)
SUPABASE_URL=YOUR_SUPABASE_URL
SUPABASE_KEY=YOUR_SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY=YOUR_SUPABASE_SERVICE_ROLE_KEY
```

### Local Setup Requirements

Before running the application, ensure you have:

1. **OpenAI API Key**: Get from https://platform.openai.com/api-keys
2. **Supabase Project**: Create at https://supabase.com and get URL/keys
3. **Supabase Setup**: Ensure pgvector extension is enabled and tables are created

## Core Architecture

### Main Components

1. **Main Entry Point** (`src/main.py`): Orchestrates the document processing workflow, handling both reception documents (접수) and regular documents (전자결재)

2. **RPA Controller** (`src/services/official_service.py`): Uses pywinauto to automate Windows applications for document processing, including approval workflows and document classification

3. **AI-Powered Services**:

   - `DocumentProcessor` (`src/services/document_processor.py`): Unified document processing service that handles both reception documents and task card matching using vector similarity
   - `SupabaseService` (`src/services/supabase_service.py`): Manages Supabase database, pgvector storage, similarity search, and CRUD operations
   - `OpenAIEmbeddingService` (`src/services/openai_embedding_service.py`): Handles OpenAI embeddings generation

4. **User Interaction** (`src/ui/console_interface.py`): Provides CLI-based user selection when automated matching isn't confident enough

### Data Flow

1. System monitors for new documents in Windows applications
2. For reception documents: finds appropriate handler and approval chain using vector similarity
3. For regular documents: matches to existing task cards using embeddings or prompts user selection
4. Uses vector embeddings for intelligent matching with learning capability
5. **Performance Optimization**: Optimized database interactions with connection pooling and batch operations

### Technology Stack

- **RPA**: pywinauto for Windows automation
- **AI/ML**: OpenAI (text-embedding-3-small) for embeddings
- **Vector Database**: Supabase pgvector for semantic search and vector storage
- **UI**: Command-line interface for user decisions
- **Configuration**: python-dotenv for environment management

## Data Management

- `data/base_data.json`: Contains predefined lists for receptions, shares, and task cards
- `data/backup/`: Stores historical processing data with timestamps
- Local embedding cache in `.cache/` directory

## Code Structure Notes

- **Unified Architecture**: `DocumentProcessor` consolidates reception and task card processing logic
- **Cloud-First**: Uses Supabase for reliable, scalable database and vector operations
- **Services follow dependency injection pattern**
- **Korean comments and variable names are used throughout**
- **Error handling focuses on graceful degradation with user fallback**
- **Vector embeddings use OpenAI's latest models for high accuracy**

## Performance Optimizations

**Current Performance Improvements:**
- **OpenAI API**: ~300-500ms per embedding (vs 800-1200ms with Ollama)
- **Supabase pgvector**: Optimized vector similarity search with native PostgreSQL performance
- **Connection Pooling**: Reuses database connections for efficiency
- **Batch Operations**: Minimizes API calls where possible

**Expected Performance:**
- Document processing: ~0.5-1 second (vs 2+ seconds previously with Ollama/Chroma)
- Vector similarity search: ~100-300ms
- Overall workflow: ~50-70% faster than previous Ollama/Chroma setup

**Migration Benefits:**
- More reliable cloud infrastructure vs local services
- Better error handling and recovery
- Scalable vector operations with pgvector
- Consistent OpenAI embedding quality
