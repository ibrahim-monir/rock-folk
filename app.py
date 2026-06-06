import streamlit as st
import lyricsgenius
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re

# --- ১. কনফিগারেশন ও এপিআই সেটআপ ---
GENIUS_TOKEN = "YOUR_GENIUS_ACCESS_TOKEN" # আপনার জেনিয়াস টোকেন এখানে বসান
SHEET_NAME = "RockFolkBD_Pipeline"        # আপনার গুগল শিটের নাম

# জেনিয়াস এপিআই ইনিশিয়েট করা
genius = lyricsgenius.Genius(GENIUS_TOKEN)

# গুগল শিট কানেকশন (Streamlit Secrets বা লোকাল ফাইল থেকে ক্রেডেনশিয়াল নেবে)
@st.cache_resource
def init_google_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # লাইভ সার্ভারে হোস্ট করলে streamlit secrets ব্যবহার করা বেস্ট
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME).sheet1

try:
    sheet = init_google_sheet()
except Exception as e:
    st.error("Google Sheet Connection Error. Please check credentials.")

# --- ২. লজিক ফাংশনসমূহ ---
def generate_conditional_prompt(mood, tempo):
    """মুড এবং টেম্পোর ওপর ভিত্তি করে কন্ডিশনাল প্রম্পট জেনারেশন লজিক"""
    if mood == 'Energetic' and 'Fast' in tempo:
        return "Upbeat Bengali folk rock, modern pop punk energy, 130 BPM, bright electric guitar solos, driving drums, powerful vocals"
    elif mood == 'Mystical' and 'Slow' in tempo:
        return "Dark alternative rock, progressive folk fusion, 75 BPM, haunting synths, heavy distorted guitar riffs, deep vocals"
    elif mood == 'Acoustic Pop':
        return "Soft rock, acoustic folk, melodic pop, 100 BPM, acoustic guitar strumming, clean emotional vocals"
    else:
        return "Modern Bengali folk fusion, energetic alternative rock, punchy live drums, high energy"

def auto_structure_lyrics(raw_lyrics):
    """র লিরিক্সকে ফিল্টার করে Suno/Udio ফ্রেন্ডলি মেটা-ট্যাগে ভাগ করার ইঞ্জিন"""
    if not raw_lyrics: return "No Lyrics Found"
    
    # জেনিয়াসের হেডার টেক্সট ও এক্সট্রা ক্যারেক্টার ক্লিন করা
    clean_text = re.sub(r'.*?Lyrics', '', raw_lyrics, count=1)
    clean_text = re.sub(r'\[.*?\]', '', clean_text) # আগের ট্যাগ থাকলে রিমুভ করা
    lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
    
    structured = ""
    if len(lines) >= 2:
        structured += "[Verse 1]\n" + "\n".join(lines[:2]) + "\n\n"
    if len(lines) > 4:
        structured += "[Chorus]\n" + "\n".join(lines[2:4]) + "\n\n"
        structured += "[Guitar Solo]\n\n[Verse 2]\n" + "\n".join(lines[4:6]) + "\n\n[Chorus]\n" + "\n".join(lines[2:4])
    else:
        structured += "[Verse 1]\n" + "\n".join(lines)
    return structured

# --- ৩. স্ট্রীমলিট লাইভ ইউজার ইন্টারফেস (UI) ---
st.set_page_config(page_title="Rock Folk BD - AI Pipeline", layout="wide")
st.title("🎸 Rock Folk BD — AI Music Production Cloud Pipeline")
st.write("২০০টি গানের অটোমেটেড লিরিক্স স্ক্র্যাপিং, কন্ডিশনাল প্রম্পট ও প্রোডাকশন ট্র্যাকার।")

menu = ["Dashboard & Tracker", "Add & Auto-Scrap Song"]
choice = st.sidebar.selectbox("Navigation Menu", menu)

# --- ট্যাব ১: ড্যাশবোর্ড এবং ট্র্যাকার ---
if choice == "Dashboard & Tracker":
    st.subheader("📊 Live Production Pipeline Tracker")
    
    # গুগল শিট থেকে ডেটা রিড করা
    data = sheet.get_all_records()
    if data:
        df = pd.DataFrame(data)
        
        # স্ট্যাটাস সামারি কাউন্টার
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Tracks", len(df))
        col2.metric("Pending Generation", len(df[df['Status'] == 'Pending']))
        col3.metric("Published to YouTube", len(df[df['Status'] == 'Published']))
        
        st.write("---")
        # ইন্টারেক্টিভ ডেটা টেবিল
        st.dataframe(df, use_container_width=True)
        
        # কুইক প্রম্পট কপিয়ার জোন
        st.subheader("⚡ Quick Copy Center")
        selected_song = st.selectbox("Select Song to Get Prompt & Lyrics", df['Title'].tolist())
        song_row = df[df['Title'] == selected_song].iloc[0]
        
        c1, c2 = st.columns(2)
        with c1:
            st.text_area("Suno/Udio Prompt (Copy Object)", song_row['Prompt'], height=70)
        with c2:
            st.text_area("Structured Lyrics (Copy Object)", song_row['Lyrics'], height=250)
            
    else:
        st.info("ডাটাবেজে কোনো গান নেই। বামদিকের মেনু থেকে গান যোগ করুন।")

# --- ট্যাব ২: নতুন গান অ্যাড ও অটো-স্ক্র্যাপ ---
elif choice == "Add & Auto-Scrap Song":
    st.subheader("🤖 Add New Song with Automation Engine")
    
    col_a, col_b = st.columns(2)
    with col_a:
        title = st.text_input("Song Title (যেমন: Khachar Vetor Ochin Pakhi)")
        artist = st.text_input("Artist/Sadok (যেমন: Lalon Shah)")
    with col_b:
        mood = st.selectbox("Select Target Mood", ["Energetic", "Mystical", "Acoustic Pop", "Heavy Metal"])
        tempo = st.selectbox("Select Target Tempo", ["Fast (120-140 BPM)", "Mid (90-110 BPM)", "Slow (70-85 BPM)"])
        
    if st.button("Scrape Lyrics & Build AI Package"):
        if title and artist:
            with st.spinner(f"Searching and Formatting '{title}' from Cloud..."):
                try:
                    # ১. অটোমেটিক গুগল/জেনিয়াস থেকে লিরিক্স স্ক্র্যাপ করা
                    genius_song = genius.search_song(title, artist)
                    raw_lyrics = genius_song.lyrics if genius_song else ""
                    
                    # ২. এআই মেটা-ট্যাগ ফরমেটিং লজিক রান করা
                    final_lyrics = auto_structure_lyrics(raw_lyrics)
                    
                    # ৩. কন্ডিশনাল লজিক দিয়ে প্রম্পট তৈরি করা
                    final_prompt = generate_conditional_prompt(mood, tempo)
                    
                    # ৪. ডেটা গুগল শিটে পুশ করা
                    next_id = f"RF-{len(sheet.get_all_records()) + 1:03d}"
                    sheet.append_row([next_id, title, artist, mood, tempo, final_prompt, final_lyrics, "Pending"])
                    
                    st.success(f"🎯 '{title}' সফলভাবে স্ক্র্যাপ করা হয়েছে এবং ক্লাউড ডাটাবেজে সেভ হয়েছে!")
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"Execution Error: {str(e)}")
        else:
            st.warning("অনুগ্রহ করে গানের নাম এবং শিল্পীর নাম ইনপুট দিন।")
