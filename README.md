# SME-Flow AI: Otonom İşletme ve Stok Asistanı

SME-Flow AI, KOBİ'ler için geliştirilmiş, **Gemini AI** destekli, otonom bir işletme ve stok yönetimi asistanıdır. Sistem, stok miktarlarını izler, kritik seviyeye inen ürünler için tedarikçilere otomatik e-posta taslakları oluşturur ve şirket sahibinin stoklara dair sorularını doğal dilde (RAG mimarisi ile) yanıtlar.

## 🚀 Özellikler

*   **Akıllı Sohbet (RAG):** İşletmenin stok durumu ve tedarikçi veritabanı üzerinden (ChromaDB vektör araması ile) halüsinasyonsuz, net yanıtlar verir.
*   **Otonom Stok Uyarıları:** Stoklar kritik seviyeye indiğinde (örn: < 10) sistemi otomatik tetikler ve ilgili tedarikçiye atılacak sipariş mailini hazırda bekletir.
*   **Hızlı ve Güvenli Backend:** FastAPI mimarisiyle saniyeler içinde yanıt veren, asenkron ve modüler bir yapı.
*   **Kullanıcı Dostu Frontend:** Streamlit üzerinden tek ekranda hem genel işletme özeti hem de AI asistan sohbet penceresi (Kişi 3 tarafından entegre edilmektedir).

## 🧠 AI & RAG Mimarisi (Agent Karar Mekanizması)

Sistemin kalbinde, **LangGraph** ile yapılandırılmış ve Google **Gemini Flash** tarafından desteklenen otonom bir AI Ajanı bulunmaktadır.

### 1. RAG (Retrieval-Augmented Generation) Sistemi
Tüm şirket verileri (ürünler, stok miktarları, tedarikçi bilgileri ve siparişler) başlangıç anında JSON formatından okunur ve **ChromaDB** vektör veritabanına indekslenir (Google Generative AI Embeddings kullanılarak). 
Kullanıcı *"Hangi ürünler azaldı?"* gibi bir soru sorduğunda:
- **Retrieval:** Ajan, `search_inventory_and_suppliers` aracı (tool) üzerinden ChromaDB'de anlamsal (semantic) arama yapar.
- **Augmented Generation:** Dönen reel stok verilerini kendi bilgi tabanına katarak "halüsinasyonsuz" ve %100 güncel bir cevap oluşturur.

### 2. Ajan (Agent) Karar Süreci & Otonom İşlemler
Ajan sadece soru yanıtlamaz, inisiyatif alır:
- **Dinamik Stok Takibi:** Sabit rakamlar yerine, son 1 aylık ortalama satış hızına (Sales History) bakılarak ürün başına **"akıllı bir sipariş eşiği"** hesaplanır.
- **Otonom E-Posta:** Stoklar eşiğin altına indiğinde, sistem ilgili ürünün tedarikçisini bulur, Gemini üzerinden acil bir **Sipariş Mail Taslağı** oluşturur ve onaya sunar.
- **Tool Calling:** Ajan, bir soru geldiğinde sırayla hangi araçları kullanacağına kendi karar verir (örn: Önce ürün kimliğini bul, sonra tedarikçi bilgilerini çek, en son rotayı planla).

## 📦 Kurulum ve Çalıştırma

### 1. Ortam Kurulumu
Projeyi klonladıktan sonra sanal ortam (virtual environment) oluşturup aktif edin:
```bash
python -m venv venv
source venv/bin/activate  # Windows için: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Çevresel Değişkenler
Ana dizinde `.env` adında bir dosya oluşturun ve Google Gemini API anahtarınızı girin:
```env
GOOGLE_API_KEY=AIzaSyYourGeminiKeyHere
```

### 3. Backend'i Ayağa Kaldırma
FastAPI sunucusunu başlatın:
```bash
cd backend
python run.py
```
API Dokümantasyonuna erişmek için: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 4. Frontend'i Başlatma
Yeni bir terminal açarak Streamlit arayüzünü başlatın:
```bash
streamlit run frontend/app.py
```
Arayüze erişmek için: [http://localhost:8501](http://localhost:8501)

## 👨‍💻 Ekip ve Görevler
*   **Kişi 1: Damla Kundak** Backend (FastAPI) ve Güvenlik
*   **Kişi 2: Semih Bekdaş** AI Asistanı, RAG Boru Hattı, ChromaDB ve Otonom Görevler
*   **Kişi 3: Ceren Altıntaş** Frontend (Streamlit) UI/UX Geliştiricisi

