import streamlit as st
import lyricsgenius
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re

# Config & Settings
GENIUS_TOKEN = "jwdd4m7rPViQYEJi7CsvPqIaZQ5cwWiQPMW8ewrzxy6xzhB-X0tPrKO6Jk2rUZEg"
SPREADSHEET_ID = "1aUYaj3-X3CYHDaOAo7OwiHsBvdaHDp1cH5TyzAAtx4s"
WORKSHEET_NAME = "Sheet1"

# Initialize Genius Client with safe headers
genius = lyricsgenius.Genius(GENIUS_TOKEN)
genius.verbose = False          
genius.remove_section_headers = True 
genius.skip_non_songs = True    
genius.retries = 3              
genius.headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

@st.cache_resource
def get_gspread_client():
    if "gcp_service_account" in st.secrets:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        return gspread.authorize(creds)
    return None

gc = get_gspread_client()

def load_pipeline_data():
    if gc:
        try:
            sh = gc.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
            records = sh.get_all_records()
            if records:
                df = pd.DataFrame(records)
                df.columns = [col.strip() for col in df.columns]
                return df
        except Exception as e:
            # Fallback to public CSV if service account fails read
            pass
            
    csv_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={WORKSHEET_NAME}"
    try:
        df = pd.read_csv(csv_url)
        df = df.dropna(how='all', axis=1)
        df.columns = [col.strip() for col in df.columns]
        return df
    except Exception as e:
        st.error(f"Sync Link Error: {str(e)}")
        return None

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

# UI Layout Setup
st.set_page_config(page_title="Rock Folk BD — Pipeline", layout="wide")
st.title("🎸 Rock Folk BD — AI Music Production Cloud Pipeline")

menu = ["Dashboard & Tracker", "Add & Auto-Scrap Song"]
choice = st.sidebar.selectbox("Navigation Menu", menu)

if choice == "Dashboard & Tracker":
    st.subheader("📊 Live Production Pipeline Tracker")
    df = load_pipeline_data()
    
    if df is not None and not df.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Tracks in Database", len(df))
        
        status_col = 'Status' if 'Status' in df.columns else ('status' if 'status' in df.columns else None)
        if status_col:
            col2.metric("Pending Generation", len(df[df[status_col].astype(str).str.lower() == 'pending']))
            col3.metric("Published to YouTube", len(df[df[status_col].astype(str).str.lower() == 'published']))
        
        st.write("---")
        st.dataframe(df, use_container_width=True)
        
        st.write("---")
        st.subheader("⚡ Quick Copy Center")
        
        title_col = 'Title' if 'Title' in df.columns else ('Song Title' if 'Song Title' in df.columns else df.columns[1])
        selected_song = st.selectbox("Select Song to Extract Assets", df[title_col].tolist())
        song_row = df[df[title_col] == selected_song].iloc[0]
        
        c1, c2 = st.columns(2)
        with c1:
            prompt_data = song_row.get('Prompt', song_row.get('Style Box Prompt (Suno/Udio)', 'N/A'))
            st.text_area("Suno/Udio Style Prompt (Copy Ready)", prompt_data, height=100)
        with c2:
            lyrics_data = song_row.get('Lyrics', song_row.get('AI Lyrics Box Format (Meta-Tags সহ)', 'N/A'))
            st.text_area("Structured Lyrics Box (Copy Ready)", lyrics_data, height=250)
    else:
        st.info("ℹ️ ডাটাবেজে বর্তমানে কোনো রেকর্ড খুঁজে পাওয়া যায়নি। অনুগ্রহ করে গুগল শিটের পারমিশন চেক করুন।")

elif choice == "Add & Auto-Scrap Song":
    st.subheader("🤖 Add New Track with Cloud Automation")
    
    col_a, col_b = st.columns(2)
    with col_a:
        title = st.text_input("Song Title")
        artist = st.text_input("Artist / Mystic Singer")
    with col_b:
        mood = st.selectbox("Select Target Mood", ["Energetic", "Melancholic", "Mystical", "Heavy Metal"])
        tempo = st.selectbox("Select Target Tempo", ["Fast (120-140 BPM)", "Mid (90-110 BPM)", "Slow (70-85 BPM)"])
        
    if st.button("Scrape Lyrics & Build Production Package"):
        if title and artist:
            if gc:
                try:
                    sh = gc.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
                    with st.spinner("Processing Automation Pipeline..."):
                        raw_lyrics = ""
                        try:
                            genius_song = genius.search_song(title, artist)
                            raw_lyrics = genius_song.lyrics if genius_song else ""
                        except:
                            st.warning("⚠️ Genius Cloudflare Protection-এর কারণে লিরিক্স অটো-স্ক্র্যাপ করা যায়নি।")
                            raw_lyrics = ""
                        
                        final_lyrics = auto_structure_lyrics(raw_lyrics)
                        final_prompt = generate_conditional_prompt(mood, tempo)
                        
                        current_df = load_pipeline_data()
                        next_id = f"RF-{len(current_df) + 1:03d}" if current_df is not None else "RF-001"
                        
                        sh.append_row([next_id, title, artist, mood, tempo, final_prompt, final_lyrics, "Pending"])
                        st.success(f"🎯 '{title}' সফলভাবে শিটে সেভ হয়েছে!")
                        st.balloons()
                except Exception as e:
                    st.error(f"Write Failure: {str(e)}")
            else:
                st.error("❌ Write Access Error: Streamlit Secrets সেটিংস চেক করুন।")
        else:
            st.warning("⚠️ অনুগ্রহ করে সব ঘর পূরণ করুন।")
