import streamlit as st
import lyricsgenius
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re

# ==============================================================================
# ১. কনফিগারেশন ও এপিআই সেটআপ (CONFIG & API SETUP)
# ==============================================================================
if "genius_token" in st.secrets:
    GENIUS_TOKEN = st.secrets["genius_token"]
else:
    GENIUS_TOKEN = "jwdd4m7rPViQYEJi7CsvPqIaZQ5cwWiQPMW8ewrzxy6xzhB-X0tPrKO6Jk2rUZEg"

# আপনার স্প্রেডশিটের ইউনিক আইডি
SPREADSHEET_ID = "1aUYaj3-X3CYHDaOAo7OwiHsBvdaHDp1cH5TyzAAtx4s"
WORKSHEET_NAME = "Sheet1"

# আপনার কোডের লাইন ২৫-এর কাছাকাছি এই সেটিংসটি যুক্ত করুন:
genius = lyricsgenius.Genius(GENIUS_TOKEN)

# আপনার রিকোয়েস্টকে ক্রোম ব্রাউজার হিসেবে মাস্ক করবে
genius.headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}


# ডাটা রিড করার জন্য পাবলিক মেথড (ক্যাশড ফিজিবিলিটি সহ)
@st.cache_data(ttl=10)  # ১০ সেকেন্ড পর পর ক্যাশ অটো-রিফ্রেশ হবে যাতে নতুন গান ড্যাশবোর্ডে দেখায়
def load_data_via_csv():
    """পাবলিক শিট থেকে সরাসরি CSV ফরমেটে ডেটা রিড করার ক্যাশড ফাংশন"""
    csv_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={WORKSHEET_NAME}"
    try:
        df = pd.read_csv(csv_url)
        df = df.dropna(how='all', axis=1)
        return df
    except Exception as e:
        st.error(f"Error fetching data via CSV link: {str(e)}")
        return None

# ডাটা রাইট বা অ্যাপেন্ড করার জন্য ক্লাউড কানেকশন
@st.cache_resource
def init_google_sheet_write():
    """ডাটা পুশ করার জন্য ক্রেডেনশিয়াল লোড করা"""
    if "gcp_service_account" in st.secrets:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
    return None

write_sheet = init_google_sheet_write()

# ==============================================================================
# ২. কোর লজিক ইঞ্জিন (DYNAMIC PROMPT & LYRICS FORMATTER)
# ==============================================================================
def generate_conditional_prompt(mood, tempo):
    if mood == 'Energetic' and 'Fast' in tempo:
        return "Upbeat Bengali folk rock, modern pop punk energy, 130 BPM, bright electric guitar solos, catchy rhythm, driving drums, cheerful powerful vocals"
    elif mood == 'Melancholic' and 'Mid' in tempo:
        return "Modern Bengali folk fusion, melodic alternative rock, mid tempo, rich acoustic guitar, deep emotional vocals, organic drums"
    elif mood == 'Mystical' and 'Slow' in tempo:
        return "Dark alternative rock, progressive folk fusion, 75 BPM, haunting atmospheric synths, deep bass, heavy distorted guitar riffs, emotional expressive vocals"
    elif mood == 'Heavy Metal':
        return "Heavy metal Bengali folk fusion, 140 BPM, shredding electric guitar solos, double bass drums, aggressive powerful vocals"
    else:
        return "Modern Bengali folk fusion, energetic alternative rock, punchy live drums, high energy"

def auto_structure_lyrics(raw_lyrics):
    if not raw_lyrics: 
        return "Lyrics Not Found. Please add manually."
    clean_text = re.sub(r'.*?Lyrics', '', raw_lyrics, count=1)
    clean_text = re.sub(r'\[.*?\]', '', clean_text)  
    lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
    
    structured = ""
    if len(lines) >= 2:
        structured += "[Verse 1]\n" + "\n".join(lines[:2]) + "\n\n"
    if len(lines) > 4:
        structured += "[Chorus]\n" + "\n".join(lines[2:4]) + "\n\n"
        structured += "[Guitar Solo]\n\n[Verse 2]\n" + "\n".join(lines[4:6]) + "\n\n[Chorus]\n" + "\n".join(lines[2:4])
        if len(lines) > 6:
            structured += "\n\n[Outro]\n[Fade Out]"
    else:
        structured += "[Verse 1]\n" + "\n".join(lines)
    return structured

# ==============================================================================
# ৩. ইউজার ইন্টারফেস (STREAMLIT APP UI)
# ==============================================================================
st.set_page_config(page_title="Rock Folk BD — Pipeline", layout="wide")
st.title("🎸 Rock Folk BD — AI Music Production Cloud Pipeline")

menu = ["Dashboard & Tracker", "Add & Auto-Scrap Song"]
choice = st.sidebar.selectbox("Navigation Menu", menu)

# --- ট্যাব ১: ড্যাশবোর্ড এবং ট্র্যাকার ---
if choice == "Dashboard & Tracker":
    st.subheader("📊 Live Production Pipeline Tracker")
    
    df = load_data_via_csv()
    if df is not None and not df.empty:
        # রিয়েল-টাইম কাউন্টার কার্ডস
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Tracks in Database", len(df))
        if 'Status' in df.columns:
            col2.metric("Pending Generation", len(df[df['Status'].astype(str).str.lower() == 'pending']))
            col3.metric("Published to YouTube", len(df[df['Status'].astype(str).str.lower() == 'published']))
        
        st.write("---")
        st.dataframe(df, use_container_width=True) # Streamlit স্ট্যান্ডার্ড অনুযায়ী আপডেট করা
        
        # কুইক কপি সেন্টার
        st.write("---")
        st.subheader("⚡ Quick Copy Center")
        
        title_col = 'Title' if 'Title' in df.columns else df.columns[1]
        selected_song = st.selectbox("Select Song to Extract Assets", df[title_col].tolist())
        song_row = df[df[title_col] == selected_song].iloc[0]
        
        c1, c2 = st.columns(2)
        with c1:
            st.text_area("Suno/Udio Style Prompt (Copy Ready)", song_row.get('Prompt', 'N/A'), height=80, use_container_width=True)
        with c2:
            st.text_area("Structured Lyrics Box (Copy Ready)", song_row.get('Lyrics', 'N/A'), height=250, use_container_width=True)
    else:
        st.info("ℹ️ ডাটাবেজে বর্তমানে কোনো রেকর্ড খুঁজে পাওয়া যায়নি অথবা কলাম হেডার অ্যাসাইন করা নেই।")

# --- ট্যাব ২: নতুন গান অ্যাড ও অটো-স্ক্র্যাপ ---
elif choice == "Add & Auto-Scrap Song":
    st.subheader("🤖 Add New Track with Cloud Automation")
    
    col_a, col_b = st.columns(2)
    with col_a:
        title = st.text_input("Song Title (যেমন: Khachar Vetor Ochin Pakhi)")
        artist = st.text_input("Artist / Mystic Singer (যেমন: Lalon Shah)")
    with col_b:
        mood = st.selectbox("Select Target Mood", ["Energetic", "Melancholic", "Mystical", "Heavy Metal"])
        tempo = st.selectbox("Select Target Tempo", ["Fast (120-140 BPM)", "Mid (90-110 BPM)", "Slow (70-85 BPM)"])
        
    if st.button("Scrape Lyrics & Build Production Package"):
        if title and artist:
            if write_sheet is not None:
                with st.spinner(f"Searching, Formatting and Syncing '{title}' to Google Sheet..."):
                    try:
                        genius_song = genius.search_song(title, artist)
                        raw_lyrics = genius_song.lyrics if genius_song else ""
                        final_lyrics = auto_structure_lyrics(raw_lyrics)
                        final_prompt = generate_conditional_prompt(mood, tempo)
                        
                        # নতুন আইডি জেনারেশন (ক্যাশ বাইপাস করে রিয়েল কাউন্ট নেওয়া)
                        csv_url_raw = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={WORKSHEET_NAME}"
                        try:
                            current_df = pd.read_csv(csv_url_raw)
                            next_id = f"RF-{len(current_df) + 1:03d}"
                        except:
                            next_id = "RF-001"
                        
                        # গুগল শিটে অ্যাপেন্ড করা
                        write_sheet.append_row([next_id, title, artist, mood, tempo, final_prompt, final_lyrics, "Pending"])
                        
                        st.success(f"🎯 '{title}' সফলভাবে প্রসেস করা হয়েছে এবং শিটে সেভ হয়েছে!")
                        st.balloons()
                        
                        # ক্যাশ ক্লিয়ার করে ড্যাশবোর্ডকে ফোর্স রিফ্রেশ করা
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Automation Engine Failure: {str(e)}")
            else:
                st.error("❌ Write Access Error: Streamlit Secrets এ '[gcp_service_account]' সেটআপ করা নেই অথবা প্রজেক্ট আইডি ভুল।")
        else:
            st.warning("⚠️ অনুগ্রহ করে গানের নাম এবং শিল্পী—উভয় বক্সই পূরণ করুন।")
