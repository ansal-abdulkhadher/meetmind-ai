import customtkinter as ctk
import soundcard as sc
import soundfile as sf
import threading
import assemblyai as aai
import os
import google.generativeai as genai
import numpy as np
import sqlite3
from datetime import datetime
import tkinter.filedialog as fd # NEW: For saving files!

# --- AI SETUP ---
aai.settings.api_key = "YOUR_ASSEMBLYAI_KEY_HERE"
genai.configure(api_key="YOUR_GEMINI_KEY_HERE")

is_recording = False
master_audio_data = [] 
recording_samplerate = 48000 
chat_session = None 

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("meetmind.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS meetings
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       date TEXT,
                       transcript TEXT,
                       insights TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- MODERN COLOR PALETTE ---
BG_APP = "#F3F5F9"        
BG_SURFACE = "#FFFFFF"    
ACCENT = "#6366F1"        
ACCENT_HOVER = "#4F46E5"  
TEXT_MAIN = "#111827"     
TEXT_MUTED = "#6B7280"    
DANGER = "#EF4444"        
DANGER_HOVER = "#DC2626"

# --- APP LOGIC ---
def toggle_meeting():
    global is_recording, master_audio_data, chat_session
    
    if is_recording:
        is_recording = False
        start_button.configure(text="Start Meeting", fg_color=ACCENT, hover_color=ACCENT_HOVER)
        transcript_box.insert("end", "\n\n--- Meeting Ended. Compiling MeetMind Intelligence... ---\n")
        transcript_box.see("end")
        
        tabs.set("AI Insights")
        result_box.delete("0.0", "end")
        result_box.insert("end", "Processing audio and generating AI insights... Please wait.\n")
        
        threading.Thread(target=process_full_meeting).start()
    else:
        is_recording = True
        master_audio_data = [] 
        chat_session = None 
        
        title.configure(text="Live Dashboard")
        start_button.configure(text="Stop Meeting", fg_color=DANGER, hover_color=DANGER_HOVER)
        
        tabs.set("Live Transcript")
        transcript_box.delete("0.0", "end")
        result_box.delete("0.0", "end")
        chat_history_box.delete("0.0", "end")
        chat_history_box.insert("end", "--- MeetMind AI Chat ---\nI will be ready to answer questions once the meeting ends!\n\n")
        
        transcript_box.insert("end", "--- Meeting Started. Listening... ---\n(Live text is a rough draft. Perfect speaker labels will generate at the end!)\n\n")
        
        threading.Thread(target=meeting_loop).start()

def meeting_loop():
    global master_audio_data, recording_samplerate
    chunk_index = 0
    
    try:
        speaker = sc.default_speaker()
        mic = sc.get_microphone(id=speaker.id, include_loopback=True)
        
        with mic.recorder(samplerate=recording_samplerate) as recorder:
            while is_recording:
                audio_chunk = recorder.record(numframes=recording_samplerate * 5)
                if not is_recording: break
                master_audio_data.append(audio_chunk)
                
                filename = f"chunk_{chunk_index}.wav"
                sf.write(filename, audio_chunk, recording_samplerate)
                threading.Thread(target=transcribe_live_chunk, args=(filename,)).start()
                chunk_index += 1
                
    except Exception as e:
        transcript_box.insert("end", f"\n[Hardware Error: {e}]\nPlease check your terminal.\n")
        transcript_box.see("end")

def transcribe_live_chunk(filename):
    try:
        config = aai.TranscriptionConfig(speech_models=["universal-2"])
        transcriber = aai.Transcriber(config=config)
        transcript = transcriber.transcribe(filename)
        
        if transcript.text:
            transcript_box.insert("end", f"{transcript.text} ")
            transcript_box.see("end")
    except Exception:
        pass 
    finally:
        if os.path.exists(filename):
            os.remove(filename)

def process_full_meeting():
    global master_audio_data, recording_samplerate, chat_session
    
    if len(master_audio_data) == 0:
        result_box.insert("end", "\nError: No audio was recorded. Check your audio devices!")
        return
        
    try:
        full_audio = np.concatenate(master_audio_data, axis=0)
        sf.write("master_meeting.wav", full_audio, recording_samplerate)
        
        config = aai.TranscriptionConfig(speech_models=["universal-2"], speaker_labels=True)
        transcriber = aai.Transcriber(config=config)
        transcript = transcriber.transcribe("master_meeting.wav")
        
        if transcript.error:
            result_box.insert("end", f"\nAssemblyAI Error: {transcript.error}")
            return
            
        full_transcript_text = ""
        for utterance in transcript.utterances:
            full_transcript_text += f"Speaker {utterance.speaker}: {utterance.text}\n"
            
        model = genai.GenerativeModel('gemini-2.5-flash')
        chat_session = model.start_chat(history=[
            {"role": "user", "parts": [f"Here is the transcript of our meeting. Please read it carefully:\n\n{full_transcript_text}"]},
            {"role": "model", "parts": ["I have read the transcript. What would you like to know?"]}
        ])
        
        prompt = "Extract the key information. Format it exactly like this:\n1. DECISIONS: List all the major things agreed upon.\n2. ACTION ITEMS: Bulleted list: * Who: [] | What: [] | By When: []"
        response = chat_session.send_message(prompt)
        
        insights_text = f"--- MEETMIND INTELLIGENCE ANALYSIS ---\n\n{response.text}"
        
        result_box.delete("0.0", "end")
        result_box.insert("end", "--- PERFECT DIARIZED TRANSCRIPT ---\n\n")
        result_box.insert("end", full_transcript_text)
        result_box.insert("end", "\n\n")
        result_box.insert("end", insights_text)

        # SAVE TO DATABASE
        conn = sqlite3.connect("meetmind.db")
        cursor = conn.cursor()
        current_date = datetime.now().strftime("%Y-%m-%d %I:%M %p")
        cursor.execute("INSERT INTO meetings (date, transcript, insights) VALUES (?, ?, ?)", 
                       (current_date, full_transcript_text, insights_text))
        conn.commit()
        conn.close()
        
        load_history_data() # Refresh the history tab so the new meeting appears

    except Exception as e:
        result_box.insert("end", f"\nError: {e}")
    finally:
        if os.path.exists("master_meeting.wav"):
            os.remove("master_meeting.wav")

def send_question(event=None):
    global chat_session
    user_question = chat_input.get()
    
    if not user_question.strip(): return
    if chat_session is None:
        chat_history_box.insert("end", "MeetMind: Please record or open a meeting first!\n\n")
        chat_input.delete(0, "end")
        return
        
    chat_history_box.insert("end", f"You: {user_question}\n")
    chat_input.delete(0, "end")
    tabs.set("Meeting Chat") 
    
    def ask_gemini():
        chat_history_box.insert("end", "MeetMind: Thinking...\n")
        chat_history_box.see("end")
        try:
            answer = chat_session.send_message(user_question)
            current_text = chat_history_box.get("0.0", "end")
            chat_history_box.delete("0.0", "end")
            chat_history_box.insert("end", current_text.replace("MeetMind: Thinking...\n", f"MeetMind: {answer.text}\n\n"))
            chat_history_box.see("end")
        except Exception as ex:
            chat_history_box.insert("end", f"Error: {ex}\n\n")
    
    threading.Thread(target=ask_gemini).start()

# --- NEW PRO FEATURES ---
def copy_to_clipboard():
    app.clipboard_clear()
    app.clipboard_append(result_box.get("0.0", "end"))
    copy_btn.configure(text="Copied!", fg_color="#10B981") # Turns green!
    app.after(2000, lambda: copy_btn.configure(text="Copy to Clipboard", fg_color=BG_APP))

def export_to_txt():
    content = result_box.get("0.0", "end")
    if len(content.strip()) < 10:
        return
        
    filepath = fd.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("Text Documents", "*.txt"), ("All Files", "*.*")],
        title="Export MeetMind Insights"
    )
    if not filepath:
        return
        
    with open(filepath, "w", encoding="utf-8") as file:
        file.write(content)

# --- NAVIGATION LOGIC ---
def show_active_meeting():
    history_frame.pack_forget()
    main_frame.pack(side="right", fill="both", expand=True)
    nav_btn_1.configure(fg_color=BG_APP, text_color=ACCENT)
    nav_btn_2.configure(fg_color="transparent", text_color=TEXT_MUTED)

def show_history():
    main_frame.pack_forget()
    history_frame.pack(side="right", fill="both", expand=True)
    nav_btn_1.configure(fg_color="transparent", text_color=TEXT_MUTED)
    nav_btn_2.configure(fg_color=BG_APP, text_color=ACCENT)
    load_history_data()

def load_history_data(search_query=""):
    for widget in history_scroll.winfo_children():
        widget.destroy()
        
    conn = sqlite3.connect("meetmind.db")
    cursor = conn.cursor()
    
    if search_query:
        # Search engine looks in both transcript and insights
        cursor.execute("SELECT id, date FROM meetings WHERE transcript LIKE ? OR insights LIKE ? ORDER BY id DESC", 
                       (f"%{search_query}%", f"%{search_query}%"))
    else:
        cursor.execute("SELECT id, date FROM meetings ORDER BY id DESC")
        
    meetings = cursor.fetchall()
    conn.close()
    
    if not meetings:
        lbl = ctk.CTkLabel(history_scroll, text="No past meetings found.", font=("Segoe UI", 16), text_color=TEXT_MUTED)
        lbl.pack(pady=40)
        return
        
    for m_id, m_date in meetings:
        card = ctk.CTkFrame(history_scroll, fg_color=BG_SURFACE, corner_radius=15)
        card.pack(fill="x", pady=10, padx=20)
        
        lbl = ctk.CTkLabel(card, text=f"Meeting: {m_date}", font=("Segoe UI", 16, "bold"), text_color=TEXT_MAIN)
        lbl.pack(side="left", padx=20, pady=20)
        
        btn = ctk.CTkButton(card, text="Open Meeting", fg_color=ACCENT, hover_color=ACCENT_HOVER, corner_radius=15, font=("Segoe UI", 14, "bold"), command=lambda i=m_id, d=m_date: open_past_meeting(i, d))
        btn.pack(side="right", padx=20)

def search_history(event=None):
    query = search_input.get()
    load_history_data(query)

def open_past_meeting(meeting_id, meeting_date):
    global chat_session
    conn = sqlite3.connect("meetmind.db")
    cursor = conn.cursor()
    cursor.execute("SELECT transcript, insights FROM meetings WHERE id=?", (meeting_id,))
    data = cursor.fetchone()
    conn.close()
    
    if data:
        transcript_text, insights_text = data
        show_active_meeting()
        title.configure(text=f"Archived Meeting ({meeting_date})")
        
        transcript_box.delete("0.0", "end")
        transcript_box.insert("end", transcript_text)
        
        result_box.delete("0.0", "end")
        result_box.insert("end", insights_text)
        
        chat_history_box.delete("0.0", "end")
        chat_history_box.insert("end", f"--- MeetMind AI Chat ---\nRestored memory for {meeting_date}. Ask me anything!\n\n")
        
        model = genai.GenerativeModel('gemini-2.5-flash')
        chat_session = model.start_chat(history=[
            {"role": "user", "parts": [f"Here is the transcript of our meeting. Please read it carefully:\n\n{transcript_text}"]},
            {"role": "model", "parts": ["I have read the transcript. What would you like to know?"]}
        ])
        tabs.set("AI Insights")

# --- USER INTERFACE ---
ctk.set_appearance_mode("light")  

app = ctk.CTk()
app.geometry("1100x750") 
app.title("MeetMind - Professional Meeting Intelligence")
app.configure(fg_color=BG_APP)

# Sidebar
sidebar = ctk.CTkFrame(app, width=240, corner_radius=0, fg_color=BG_SURFACE)
sidebar.pack(side="left", fill="y")

logo_label = ctk.CTkLabel(sidebar, text="MeetMind.", font=("Segoe UI", 28, "bold"), text_color=ACCENT)
logo_label.pack(pady=(40, 5), padx=20, anchor="w")

subtitle_label = ctk.CTkLabel(sidebar, text="Intelligence Hub", font=("Segoe UI", 13, "bold"), text_color=TEXT_MUTED)
subtitle_label.pack(pady=(0, 40), padx=22, anchor="w")

nav_btn_1 = ctk.CTkButton(sidebar, text="  Active Workspace", fg_color=BG_APP, text_color=ACCENT, hover_color="#E0E7FF", font=("Segoe UI", 14, "bold"), anchor="w", corner_radius=15, height=45, command=show_active_meeting)
nav_btn_1.pack(pady=10, padx=20, fill="x")

nav_btn_2 = ctk.CTkButton(sidebar, text="  Meeting Vault", fg_color="transparent", text_color=TEXT_MUTED, hover_color="#E0E7FF", font=("Segoe UI", 14, "bold"), anchor="w", corner_radius=15, height=45, command=show_history)
nav_btn_2.pack(pady=5, padx=20, fill="x")

# Main Content Area
main_frame = ctk.CTkFrame(app, corner_radius=0, fg_color="transparent")
main_frame.pack(side="right", fill="both", expand=True)

header = ctk.CTkFrame(main_frame, fg_color="transparent")
header.pack(fill="x", pady=(30, 20), padx=40)

title = ctk.CTkLabel(header, text="Live Dashboard", font=("Segoe UI", 26, "bold"), text_color=TEXT_MAIN)
title.pack(side="left")

start_button = ctk.CTkButton(header, text="Start Meeting", fg_color=ACCENT, hover_color=ACCENT_HOVER, font=("Segoe UI", 15, "bold"), text_color=BG_SURFACE, corner_radius=25, width=160, height=45, command=toggle_meeting)
start_button.pack(side="right")

tabs = ctk.CTkTabview(main_frame, fg_color=BG_SURFACE, text_color=TEXT_MAIN, segmented_button_selected_color=ACCENT, segmented_button_selected_hover_color=ACCENT_HOVER, segmented_button_unselected_color=BG_APP, segmented_button_unselected_hover_color="#E2E8F0", corner_radius=15)
tabs.pack(fill="both", expand=True, padx=40, pady=(0, 40))

tabs.add("Live Transcript")
tabs.add("AI Insights")
tabs.add("Meeting Chat")

transcript_box = ctk.CTkTextbox(tabs.tab("Live Transcript"), font=("Segoe UI", 15), wrap="word", fg_color=BG_SURFACE, text_color=TEXT_MAIN, spacing1=5)
transcript_box.pack(fill="both", expand=True, padx=20, pady=20)

# INSIGHTS TAB WITH NEW ACTION BUTTONS
result_box = ctk.CTkTextbox(tabs.tab("AI Insights"), font=("Segoe UI", 15), wrap="word", fg_color=BG_SURFACE, text_color=TEXT_MAIN, spacing1=5)
result_box.pack(fill="both", expand=True, padx=20, pady=(20, 10))

actions_frame = ctk.CTkFrame(tabs.tab("AI Insights"), fg_color="transparent")
actions_frame.pack(fill="x", padx=20, pady=(0, 10))

copy_btn = ctk.CTkButton(actions_frame, text="Copy to Clipboard", fg_color=BG_APP, text_color=ACCENT, hover_color="#E0E7FF", font=("Segoe UI", 14, "bold"), corner_radius=15, height=35, command=copy_to_clipboard)
copy_btn.pack(side="left", padx=(0, 10))

export_btn = ctk.CTkButton(actions_frame, text="Export as .TXT", fg_color=ACCENT, hover_color=ACCENT_HOVER, font=("Segoe UI", 14, "bold"), corner_radius=15, height=35, command=export_to_txt)
export_btn.pack(side="left")

chat_history_box = ctk.CTkTextbox(tabs.tab("Meeting Chat"), font=("Segoe UI", 15), wrap="word", fg_color=BG_APP, text_color=TEXT_MAIN, corner_radius=15, spacing1=8)
chat_history_box.pack(fill="both", expand=True, padx=20, pady=(20, 10))

chat_frame = ctk.CTkFrame(tabs.tab("Meeting Chat"), fg_color="transparent")
chat_frame.pack(fill="x", padx=20, pady=(10, 20))

chat_input = ctk.CTkEntry(chat_frame, placeholder_text="Ask MeetMind a question...", font=("Segoe UI", 15), height=50, corner_radius=25, fg_color=BG_APP, border_width=0, text_color=TEXT_MAIN)
chat_input.pack(side="left", fill="x", expand=True, padx=(0, 15))
chat_input.bind('<Return>', send_question)

send_button = ctk.CTkButton(chat_frame, text="Send", width=110, height=50, font=("Segoe UI", 15, "bold"), fg_color=TEXT_MAIN, hover_color="#374151", corner_radius=25, command=send_question)
send_button.pack(side="right")

# History Content Area (With Search Bar!)
history_frame = ctk.CTkFrame(app, corner_radius=0, fg_color="transparent")

history_header = ctk.CTkFrame(history_frame, fg_color="transparent")
history_header.pack(fill="x", pady=(30, 20), padx=40)

history_title = ctk.CTkLabel(history_header, text="Meeting Vault", font=("Segoe UI", 26, "bold"), text_color=TEXT_MAIN)
history_title.pack(side="left")

# Search UI
search_frame = ctk.CTkFrame(history_frame, fg_color="transparent")
search_frame.pack(fill="x", padx=40, pady=(0, 10))

search_input = ctk.CTkEntry(search_frame, placeholder_text="Search past meetings by keyword...", font=("Segoe UI", 15), height=45, corner_radius=20, fg_color=BG_SURFACE, border_width=0, text_color=TEXT_MAIN)
search_input.pack(side="left", fill="x", expand=True, padx=(0, 10))
search_input.bind('<Return>', search_history)

search_btn = ctk.CTkButton(search_frame, text="Search", font=("Segoe UI", 14, "bold"), width=100, height=45, corner_radius=20, fg_color=ACCENT, hover_color=ACCENT_HOVER, command=search_history)
search_btn.pack(side="right")

history_scroll = ctk.CTkScrollableFrame(history_frame, fg_color="transparent")
history_scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))

app.mainloop()