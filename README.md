# MeetMind - Professional Meeting Intelligence

### The Problem
In modern remote workflows, tracking crucial decisions, assigning action items, and recalling specific conversational context is incredibly difficult. Participants often lose focus taking manual notes, and traditional transcripts lack the intelligence to differentiate speakers or extract actionable next steps.

### The Solution
MeetMind is a lightweight, AI-powered desktop application that acts as a live meeting assistant. It seamlessly captures system audio, processes it through advanced speaker diarization to identify individual participants, and leverages an LLM to automatically generate structured "Decisions" and "Action Items." It features an integrated AI Chatbot for querying past context and a local SQLite database for a persistent Meeting Vault.

### Tech Stack
* **Language:** Python 3.10+
* **UI Framework:** CustomTkinter
* **Transcription & Diarization:** AssemblyAI API (Universal-2 Model)
* **Intelligence & Extraction:** Google Gemini 2.5 Flash API
* **Audio Processing:** Soundcard, Soundfile, NumPy
* **Database:** SQLite3

### Setup Instructions
1. Clone this repository to your local machine.
2. Create and activate a virtual environment.
3. Install the required dependencies:
   `pip install customtkinter soundcard soundfile assemblyai google-generativeai numpy`
4. Open `main.py` and insert your own AssemblyAI and Gemini API keys at the top of the file.
5. Run the application:
   `python main.py`
6. Open main.py and insert the API keys. (Note for Judges: For your convenience, I have provided active testing keys in the private comments of my submission form!)"

To make testing easier for the evaluators, I have provided my active API keys  so you don't have to create your own. Please paste these into lines 12 and 13 of main.py to run the app instantly: "
AssemblyAI: [Your Key]
Gemini: [Your Key]


## 🎥 Project Demo

Watch the demo here:
https://drive.google.com/file/d/1aduciKCbCWJ6hYHtDSaJJNhd7X5Z2VX3/view?usp=sharing
