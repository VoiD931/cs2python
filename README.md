# Counter Strike 2 ESP and Aimbot (Python)

This project outlines the structure and provides initial code for an ESP (Extra Sensory Perception) and Aimbot for Counter Strike 2, written in Python. It directly interacts with game memory for reading and potentially writing data.

## **Disclaimer:**
Using memory-reading/writing tools in online games like Counter Strike 2 is against the game's Terms of Service and can result in a permanent ban. This project is provided for educational purposes only, to demonstrate how such tools function, and for security research into game anti-cheat mechanisms. Use at your own risk in environments where you have explicit permission.

## Features (Planned/Conceptualized):
- **ESP:** Displaying information about players (health, position) through an overlay.
- **Aimbot:** Automatically adjusting mouse movement to aim at enemy players.
- **Memory Interaction:** Direct reading and writing to game process memory.

## Project Structure:
- `main.py`: The entry point for the application. Initializes configuration, memory access, ESP, and Aimbot modules, then runs the main loop.
- `config.py`: Stores configuration settings, including process names, screen resolution, and critical game memory offsets. **NOTE: Offsets are placeholders and must be updated for the current game version.**
- `esp.py`: Handles the logic for ESP features, including reading entity data and conceptual methods for drawing overlays.
- `aimbot.py`: Contains the aimbot logic, such as finding targets, calculating aiming angles, and simulating mouse input.
- `utils.py`: Provides helper functions for interacting with Windows API (memory reading/writing, process enumeration, mouse input) and mathematical calculations for aimbot.
- `requirements.txt`: Lists Python dependencies (currently none beyond built-in modules).
- `README.md`: Project overview and setup instructions.

## Setup:
1.  **Operating System:** This project is currently designed for Windows due to its reliance on `ctypes` and Windows API calls (`kernel32`, `psapi`, `user32`).
2.  **Python:** Ensure you have Python 3.x installed.
3.  **Dependencies:** As of now, all necessary modules (`ctypes`, `math`, `sys`, `time`) are part of Python's standard library. No `pip install` is strictly required for the core functionality.
    ```bash
    # pip install -r requirements.txt # (if external libraries were added later)
    ```

## Configuration:
Before running, you **MUST** update the `offsets` dictionary in `config.py`. Game offsets change frequently with patches. You will need to use tools like:
-   **Cheat Engine:** To manually find memory addresses and offsets.
-   **Public Offset Dumpers:** Websites or tools that provide up-to-date offsets for CS2.

Example placeholders in `config.py`:
```python
        self.offsets = {
            "local_player": 0x00000000, # Base address for the local player object
            "entity_list": 0x00000000,  # Base address for the entity list
            "health": 0x00000000,       # Offset from player base to health value
            "position": 0x00000000,     # Offset from player base to position vector (X, Y, Z)
            "view_angle": 0x00000000    # Offset from player base to view angles (Pitch, Yaw)
        }
```

## How to Run:
1.  Ensure Counter Strike 2 is running.
2.  Update the offsets in `config.py` to match the current game version.
3.  Execute the `main.py` script:
    ```bash
    python main.py
    ```

## Development Notes:
-   **ESP Overlay:** The `esp.py` currently has placeholder `draw_box` methods. A real ESP would require an external overlay solution (e.g., a transparent PyQt/PySide window, or direct GDI/DirectX drawing via more advanced `ctypes` usage or external libraries).
-   **Aimbot Input:** The `mouse_move_relative` function in `utils.py` uses `user32.mouse_event` for external mouse control. For a more robust and less detectable aimbot, you would ideally write directly to the game's view angle memory addresses, which requires deeper anti-anti-cheat bypass techniques.
-   **Error Handling:** Basic error handling is present, but could be expanded for more robust operation, especially around memory access.
-   **Anti-Cheat:** This basic implementation is highly detectable by modern anti-cheat systems. Bypassing anti-cheat requires advanced techniques (e.g., driver-level memory access, obfuscation, polymorphic code, anti-debugging, etc.) which are not included here.

This project provides a foundational framework. Expanding its capabilities requires continuous research into game memory structures and anti-cheat systems.