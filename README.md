# Rhythm Game Architecture

This repository outlines the core architecture for a rhythm game, handling everything from scene transitions and UI to precise audio timing and optimized note rendering. 

## System Architecture Overview

The game's structure is divided into several interconnected systems, as defined in our core UML design:

### 1. Scene Management (App Flow)
The central flow of the application is managed by a state-based scene router.
* **`SceneManager`**: The top-level controller that maintains a registry of scenes and handles switching the active scene. It delegates all event processing and draw calls to the currently active scene.
* **`Scene` (Abstract Base Class)**: Provides a standard template enforcing lifecycle and loop methods (`handle_events`, `update`, `draw`, `on_enter`, `on_exit`).
* **Implementations**: Includes menus (`MainMenuScene`), game setup (`CalibrationScene`, `ImportAudioScene`), the main loop (`GameplayScene`), and post-game screens (`ResultsScene`).

### 2. The Gameplay Hub
* **`GameplayScene`**: The most complex component, acting as the central hub during active gameplay. It aggregates the timing system (`Conductor`), the level data (`Song`), visual objects (`NodePool`), user controls (`InputHandler`), and the scoring system (`Player`).

### 3. Audio & Timing Core
Precise timing is the most critical element of a rhythm game. This architecture separates the track data from the real-time execution.
* **`Conductor`**: The game's internal "metronome". It tracks the exact `song_position`, manages visual offsets, and dictates where notes should be drawn on the screen based on current time and scroll speed.
* **`Song`**: A data container holding track metadata (`name`, `bpm`, audio file path) and a strict ordered list of `NoteTarget` objects.
* **`ChartParser`**: A utility that parses external beatmap/chart files and instantiates the `Song` and `NoteTarget` objects.

### 4. Note Rendering & Object Pooling
To maintain high frame rates (essential for rhythm games) when rendering thousands of notes, the system utilizes an object pooling optimization pattern.
* **`NoteTarget`**: The raw *data* representing a note. It knows its target lane, beat/row index, and whether it has been hit or missed.
* **`Node`**: The *visual representation* of a note. It contains the image surfaces (e.g., tap surface, hold body/tail surfaces) and render logic.
* **`NodePool`**: Instead of continuously creating and destroying objects (which causes garbage collection stutter), the pool pre-allocates a fixed number (`POOL_SIZE`) of `Node` objects. The active scene calls `acquire()` to display a note and `release()` to return it to the pool once it passes the hit window.

### 5. Player Input & Scoring
* **`InputHandler`**: Maps raw hardware inputs (keyboard/controller events) into logical game lanes, tracking precisely when lanes are pressed and released.
* **`Player`**: Manages the user's session states (`score`, `streak`, `health`, multiplier). It features a critical `judge(error_ms)` method, which evaluates the timing delta between a player's input and the note's perfect target time to award accuracy ratings (Perfect, Good, OK, Miss).
