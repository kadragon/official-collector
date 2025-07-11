# GEMINI

## Coding Guideline

### Using Context 7 MCP When Utilizing Libraries

1. When utilizing any libraries in your code, always review and verify the contents of **context 7 MCP**.
2. Ensure that all requirements and constraints from context 7 MCP are considered and appropriately applied when implementing or integrating libraries.
3. After completing your implementation with libraries, re-check compliance with context 7 MCP and make necessary adjustments if needed.
4. Failure to review or apply context 7 MCP when using libraries may result in code review rejection.
5. Clearly document your context 7 MCP verification process and how its requirements have been addressed in your code or pull request (PR) when using libraries.

## Project Structure

This project follows a modular structure to ensure maintainability and scalability. Key directories and their roles are:

- **`src/`**: Contains all source code for the application.
  - **`config.py`**: Handles environment variable loading and application-wide configurations.
  - **`main.py`**: The main entry point of the application, orchestrating the overall flow.
  - **`services/`**: Contains all core business logic and service modules, including interactions with external APIs (e.g., Supabase) and internal components (e.g., RPA collector, dialogs).
    - `command_executor.py`: Executes system commands.
    - `dialog_service.py`: Manages user interactions and dialogs.
    - `official_collector.py`: Handles the collection of official documents.
    - `reception_service.py`: Processes incoming official documents.
    - `supabase_service.py`: Manages interactions with the Supabase backend.
    - `task_card_service.py`: Handles the matching and management of task cards.
  - **`utils/`**: Provides general utility functions that are not specific to any particular business logic.
    - `json_handler.py`: Utility for handling JSON data.
    - `prompt.py`: Manages prompts for AI interactions.
