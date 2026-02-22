import streamlit as st
import feedparser
import google.generativeai as genai
from openai import OpenAI
import time
from newspaper import Article

# --- KONFİGÜRASYON (API ANAHTARLARI) ---
GEMINI_KEY = "AIzaSyBdWQKVLMGXbMffMobpvfXOKXn9CCJWvCI"
GPT_KEY = "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"

# Yapay Zeka Servislerini Başlat
genai.configure(api_key=GEMINI_KEY)
client = OpenAI(api_key=GPT_KEY)

# --- SAYFA AYARLARI VE TASARIM ---
st.set_page_config(page_title="ORTADOGU ANALIZ SISTEMI", layout="wide")

st.markdown("""
    <style>
    /* Kurumsal Koyu Tema */
    .stApp { background-color: #0e1117; color: #ffffff; }
    
    /* Haber Kartı Tasarımı */
    .news-card {
        background-color: #1a1c23;
        border: 1px solid #2d2f39;
        border-radius: 10px;
        padding: 25px;
        margin-bottom: 30px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    }
    
    /* Başlık ve Metin Stilleri */
    .news-title { color: #e0e0e0; font-size: 24px; font-weight: 600; margin-bottom: 15px; }
    .content-area { color: #bcbcbc; line-height: 1.7; font-size: 16px; }
    .meta-data { color: #555; font-size: 12px; margin-top: 10px; text-transform: uppercase; }
    
    /* Sidebar Stili */
    section[data-testid="stSidebar"] { background-color: #111318 !important; border-right: 1px solid #2d2f39; }
    </style>
    """, unsafe_allow_html=True)

# --- YAN PANEL (SIDEBAR) ---
st.sidebar.title("KONTROL MERKEZİ")
st.sidebar.markdown("---")

# Filtreler
search_keywords = st.sidebar.text_input("TAKİP ANAHTAR KELİMELERİ", "Gaza, Israel, Iran, Lebanon, Syria")
keyword_list = [k.strip().lower() for k in search_keywords.split(",")]

# Kaynaklar
sources = {
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "Reuters ME": "https://www.reutersagency.com/feed/?best-topics=middle-east&post_type=best",
    "BBC ME": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
    "Middle East Eye": "https://www.middleeasteye.net/rss",
    "Times of Israel": "https://www.timesofisrael.com/feed/"
}
selected_sources = st.sidebar.multiselect("KAYNAK SEÇİMİ", list(sources.keys()), default=list(sources.keys())[:3])

# Hız Ayarları
st.sidebar.markdown("---")
show_images = st.sidebar.toggle("GÖRSELLERİ YÜKLE", value=False)
fetch_full_text = st.sidebar.toggle("TAM METİN ANALİZİ", value=True)
auto_refresh = st.sidebar.checkbox("OTOMATİK YENİLEME AKTİF")
refresh_min = st.sidebar.slider("YENİLEME SIKLIĞI (DK)", 1, 60, 15)

# --- FONKSİYONLAR (HATA GİDERİLMİŞ) ---

@st.cache_data(ttl=3600)
def get_clean_entries(url):
    """Haber verisini temizleyerek belleğe alır ve I/O hatalarını engeller."""
    feed = feedparser.parse(url)
    clean_data = []
    for entry in feed.entries[:10]:
        clean_data.append({
            'title': entry.get('title', ''),
            'link': entry.get('link', ''),
            'summary': entry.get('summary', '')
        })
    return clean_data

def ai_analyze(title, text):
    """Hibrit AI motoru: Önce Gemini, hata durumunda GPT."""
    prompt = f"""
    Sen kıdemli bir dış haberler analizcisisin. Aşağıdaki İngilizce haberi profesyonel bir dille Türkçeye çevir ve analiz et.
    Başlık: {title}
    İçerik: {text[:3500]}
    
    Format:
    [BAŞLIK ÇEVİRİSİ]
    ANALİZ: (Haberin stratejik önemi hakkında 1-2 cümle)
    DETAY: (Haberin tam Türkçe çevirisi)
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text, "GEMINI"
    except:
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content, "GPT-4"
        except Exception as e:
            return f"Analiz hatası: {e}", "HATA"

# --- ANA AKIŞ ---
st.title("🌍 ORTADOĞU HABER İSTİHBARAT AKIŞI")

if st.button("VERİLERİ GÜNCELLE") or auto_refresh:
    for name in selected_sources:
        st.subheader(f"📍 {name}")
        entries = get_clean_entries(sources[name])
        
        for entry in entries:
            # Filtre kontrolü
            combined_content = (entry['title'] + " " + entry['summary']).lower()
            if any(kw in combined_content for kw in keyword_list):
                
                with st.container():
                    st.markdown('<div class="news-card">', unsafe_allow_html=True)
                    
                    final_content = entry['summary']
                    display_image = None
                    
                    # Tam metin ve görsel çekme (İsteğe bağlı)
                    if fetch_full_text or show_images:
                        try:
                            article = Article(entry['link'])
                            article.download()
                            article.parse()
                            if fetch_full_text: final_content = article.text
                            if show_images: display_image = article.top_image
                        except:
                            pass

                    if display_image:
                        st.image(display_image, use_container_width=True)
                    
                    # AI İşleme
                    with st.spinner('Analiz ediliyor...'):
                        result, motor = ai_analyze(entry['title'], final_content)
                        st.markdown(f"<div class='content-area'>{result}</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='meta-data'>KAYNAK: {name} | MOTOR: {motor}</div>", unsafe_allow_html=True)
                        st.caption(f"[KAYNAK LİNKİNE GİT]({entry['link']})")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                    time.sleep(1) # API limit koruması

# Otomatik Yenileme Mantığı
if auto_refresh:
    time.sleep(refresh_min * 60)
    st.rerun()