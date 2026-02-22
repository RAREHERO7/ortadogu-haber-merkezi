import streamlit as st
import feedparser
import google.generativeai as genai
from openai import OpenAI
import time
from newspaper import Article

# --- GÜVENLİ API YAPILANDIRMASI ---
# GitHub'ın anahtarı iptal etmemesi için Secrets yapısını kullanıyoruz.
# Eğer yerelde (PC) çalıştıracaksanız buraya geçici olarak anahtarınızı yazabilirsiniz.
try:
    GEMINI_KEY = st.secrets["GEMINI_KEY"]
    GPT_KEY = st.secrets["GPT_KEY"]
except:
    # Arkadaşın için kolaylık: Eğer secrets ayarı yapılmamışsa manuel giriş alanı
    GEMINI_KEY = st.sidebar.text_input("Gemini API Key", type="password")
    GPT_KEY = st.sidebar.text_input("OpenAI API Key", type="password")

# API Servislerini Başlat
if GEMINI_KEY: genai.configure(api_key=GEMINI_KEY)
if GPT_KEY: client = OpenAI(api_key=GPT_KEY)

# --- ARAYÜZ VE TASARIM ---
st.set_page_config(page_title="ORTADOGU ANALIZ MERKEZI", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .news-card {
        background-color: #1a1c23;
        border: 1px solid #2d2f39;
        border-radius: 10px;
        padding: 25px;
        margin-bottom: 30px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    }
    .content-area { color: #bcbcbc; line-height: 1.7; font-size: 16px; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.title("KONTROL PANELİ")
search_keywords = st.sidebar.text_input("TAKİP ANAHTAR KELİMELERİ", "Gaza, Israel, Iran, Lebanon, Syria")
keyword_list = [k.strip().lower() for k in search_keywords.split(",")]

sources = {
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "Reuters ME": "https://www.reutersagency.com/feed/?best-topics=middle-east&post_type=best",
    "BBC ME": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
    "Middle East Eye": "https://www.middleeasteye.net/rss"
}
selected_sources = st.sidebar.multiselect("KAYNAK SEÇİMİ", list(sources.keys()), default=list(sources.keys())[:2])

show_images = st.sidebar.toggle("GÖRSELLERİ YÜKLE", value=False)
fetch_full_text = st.sidebar.toggle("TAM METİN ANALİZİ", value=True)

# --- FONKSİYONLAR ---
@st.cache_data(ttl=3600)
def get_clean_entries(url):
    feed = feedparser.parse(url)
    return [{'title': e.get('title', ''), 'link': e.get('link', ''), 'summary': e.get('summary', '')} for e in feed.entries[:8]]

def ai_analyze(title, text):
    prompt = f"Analyze and translate this Middle East news to Turkish:\nTitle: {title}\nText: {text[:3000]}"
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        return model.generate_content(prompt).text, "GEMINI"
    except:
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content, "GPT-4"
        except:
            return "Analiz motoru şu an meşgul.", "HATA"

# --- ANA AKIŞ ---
st.title("🌍 ORTADOĞU HABER İSTİHBARAT AKIŞI")

if st.button("VERİLERİ GÜNCELLE"):
    if not GPT_KEY:
        st.error("Lütfen bir API anahtarı girin veya Secrets ayarını yapın.")
    else:
        for name in selected_sources:
            entries = get_clean_entries(sources[name])
            for entry in entries:
                if any(kw in (entry['title'] + entry['summary']).lower() for kw in keyword_list):
                    with st.container():
                        st.markdown('<div class="news-card">', unsafe_allow_html=True)
                        
                        f_text = entry['summary']
                        img = None
                        if fetch_full_text or show_images:
                            try:
                                art = Article(entry['link'])
                                art.download(); art.parse()
                                if fetch_full_text: f_text = art.text
                                if show_images: img = art.top_image
                            except: pass

                        if img: st.image(img, use_container_width=True)
                        
                        res, engine = ai_analyze(entry['title'], f_text)
                        st.markdown(f"<div class='content-area'>{res}</div>", unsafe_allow_html=True)
                        st.caption(f"KAYNAK: {name} | MOTOR: {engine} | [LİNK]({entry['link']})")
                        st.markdown('</div>', unsafe_allow_html=True)
                        time.sleep(1)
