import streamlit as st
import lyricsgenius
import pandas as pd
import gspread
import re

# ==============================================================================
# ১. কনফিগারেশন ও এপিআই সেটআপ (CONFIG & API SETUP)
# ==============================================================================
# Streamlit Secrets থেকে জেনিয়াস টোকেন লোড করা (অথবা আপনার দেওয়া ডিফল্ট টোকেন)
if "genius_token" in st.secrets:
    GENIUS_TOKEN = st.secrets["genius_token"]
else:
    GENIUS_TOKEN = "jwdd4m7rPViQYEJi7CsvPqIaZQ5cwWiQPMW8ewrzxy6xzhB-X0tPrKO6Jk2rUZEg"

# আপনার নতুন গুগল স্প্রেডশিট ফাইলের নাম এবং ভেতরের সাব-শিটের নাম
SHEET_NAME = "Lyrics & Prompts Matrix"  
WORKSHEET_NAME = "Sheet1"

# জেনিয়াস এপিআই অবজেক্ট তৈরি
genius = lyricsgenius.Genius(GENIUS_TOKEN)

@st.cache_resource
def init_public_google_sheet():
    """পাবলিকলি শেয়ার করা (Anyone with link can edit) গুগল শিটের সাথে ক্রেডেনশিয়াল ছাড়া কানেক্ট করার মেথড"""
    # ক্রেডেনশিয়াল ছাড়া ওপেন ক্লায়েন্ট হিসেবে gspread কানেক্ট করা
    client = gspread.public() 
    # পাবলিক শিটের কি (URL থেকে নেওয়া) ব্যবহার করে সরাসরি ওয়ার্কশিট ওপেন করা
    sheet_key = "1cIGldrClS15iN2MfOapN1m9TdbBdJ7oPIdsruRraiHw"
    return client.open_by_key(sheet_key).worksheet(WORKSHEET_NAME)

sheet = None
try:
    sheet = init_public_google_sheet()
except Exception as e:
    st.error(f"❌ Google Sheet Connection Error: {str(e)}")
    st.info("💡 সমাধান: নিশ্চিত করুন আপনার গুগল শিটের 'Anyone with the link can edit' অপশনটি সঠিকভাবে চালু আছে কি না।")

# ==============================================================================
# ২. কোর লজিক ইঞ্জিন (DYNAMIC PROMPT & LYRICS FORMATTER)
# ==============================================================================
def generate_conditional_prompt(mood, tempo):
    """মুড ও টেম্পোর ওপর ভিত্তি করে Suno/Udio প্রম্পট তৈরি করে"""
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
    """র লিরিক্সকে [Verse] এবং [Chorus] মেটা-ট্যাগে সাজায়"""
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
st.write("২০০টি গানের অটোমেটেড ক্লাউড ডাটাবেজ, লিরিক্স স্ক্র্যাপিং এবং কন্ডিশনাল প্রম্পট পাইপলাইন।")

menu = ["Dashboard & Tracker", "Add & Auto-Scrap Song"]
choice = st.sidebar.selectbox("Navigation Menu", menu)

# --- ট্যাব ১: ড্যাশবোর্ড এবং ট্র্যাকার ---
if choice == "Dashboard & Tracker":
    st.subheader("📊 Live Production Pipeline Tracker")
    
    if sheet is not None:
        try:
            data = sheet.get_all_records()
            if data:
                df = pd.DataFrame(data)
                
                # রিয়েল-টাইম কাউন্টার কার্ডস
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Tracks in Database", len(df))
                col2.metric("Pending Generation", len(df[df['Status'].str.lower() == 'pending']) if 'Status' in df.columns else 0)
                col3.metric("Published to YouTube", len(df[df['Status'].str.lower() == 'published']) if 'Status' in df.columns else 0)
                
                st.write("---")
                st.dataframe(df, use_container_width=True)
                
                # কুইক কপি সেন্টার
                st.write("---")
                st.subheader("⚡ Quick Copy Center")
                
                title_col = 'Title' if 'Title' in df.columns else df.columns[1]
                selected_song = st.selectbox("Select Song to Extract Assets", df[title_col].tolist())
                song_row = df[df[title_col] == selected_song].iloc[0]
                
                c1, c2 = st.columns(2)
                with c1:
                    st.text_area("Suno/Udio Style Prompt (Copy Ready)", song_row.get('Prompt', 'N/A'), height=80)
                with c2:
                    st.text_area("Structured Lyrics Box (Copy Ready)", song_row.get('Lyrics', 'N/A'), height=250)
            else:
                st.info("ℹ️ ডাটাবেজে কোনো গান নেই। বামদিকের মেনু থেকে 'Add & Auto-Scrap Song' সিলেক্ট করে গান যোগ করুন।")
        except Exception as e:
            st.error(f"Error reading records: {str(e)}")
    else:
        st.warning("⚠️ ক্লাউড ডাটাবেজের সাথে কানেকশন এস্টাবলিশড নেই।")

# --- ট্যাব ২: নতুন গান অ্যাড ও অটো-স্ক্র্যাপ ---
elif choice == "Add & Auto-Scrap Song":
    st.subheader("🤖 Add New Track with Cloud Automation")
    
    if sheet is not None:
        col_a, col_b = st.columns(2)
        with col_a:
            title = st.text_input("Song Title (যেমন: Khachar Vetor Ochin Pakhi)")
            artist = st.text_input("Artist / Mystic Singer (যেমন: Lalon Shah)")
        with col_b:
            mood = st.selectbox("Select Target Mood", ["Energetic", "Melancholic", "Mystical", "Heavy Metal"])
            tempo = st.selectbox("Select Target Tempo", ["Fast (120-140 BPM)", "Mid (90-110 BPM)", "Slow (70-85 BPM)"])
            
        if st.button("Scrape Lyrics & Build Production Package"):
            if title and artist:
                with st.spinner(f"Searching, Formatting and Syncing '{title}' to Google Sheet..."):
                    try:
                        # ১. ক্লাউড থেকে অটোমেটিক লিরিক্স স্ক্র্যাপ
                        genius_song = genius.search_song(title, artist)
                        raw_lyrics = genius_song.lyrics if genius_song else ""
                        
                        # ২. এআই মেটা-ট্যাগ মেথডে লিরিক্স সাজানো
                        final_lyrics = auto_structure_lyrics(raw_lyrics)
                        
                        # ৩. কন্ডিশনাল লজিক দিয়ে প্রম্পট তৈরি
                        final_prompt = generate_conditional_prompt(mood, tempo)
                        
                        # ৪. গুগল শিটের লাস্ট রো-তে ডেটা পুশ করা
                        total_rows = len(sheet.get_all_records())
                        next_id = f"RF-{total_rows + 1:03d}"
                        
                        sheet.append_row([next_id, title, artist, mood, tempo, final_prompt, final_lyrics, "Pending"])
                        
                        st.success(f"🎯 '{title}' সফলভাবে প্রসেস করা হয়েছে এবং 'Lyrics & Prompts Matrix' শিটে সেভ হয়েছে!")
                        st.balloons()
                        
                    except Exception as e:
                        st.error(f"Automation Engine Failure: {str(e)}")
            else:
                st.warning("⚠️ অনুগ্রহ করে গানের নাম এবং শিল্পী—উভয় বক্সই পূরণ করুন।")
