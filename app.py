"""
EN²TECH 2026 – Enerji Pusulası MVP
===================================
OSB KOBİ ve orta ölçekli üretim tesisleri için
veri temelli enerji dönüşümü yatırım önceliklendirme
ve hızlı ön fizibilite arayüzü.

Bu araç detaylı mühendislik fizibilitesinin yerine geçmez.
Hızlı ön fizibilite ve yatırım önceliklendirme amacıyla çalışır.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO

# ============================================================
# SABİTLER VE VARSAYIMLAR
# ============================================================

# Ana karar kriterleri ağırlıkları
KRITER_AGIRLIKLARI = {
    "ekonomik_cekicilik": 0.30,
    "teknik_uygunluk": 0.25,
    "performans_iyilestirme_potansiyeli": 0.20,
    "uygulanabilirlik": 0.15,
    "cevresel_etki": 0.10,
}

# GES üretim sabiti (kWh/kWp-yıl)
YILLIK_GES_URETIM_SABITI = 1500

# Çatı alanı -> kurulu güç dönüşümü (m2/kWp)
PV_M2_PER_KWP = 7

# GES yatırım birim maliyeti (TL/kWp)
YATIRIM_SABITI_GES_TL_PER_KWP = 18000

# GES çatı uygunluk çarpanları
CATI_UYGUNLUK_CARPANI = {
    "uygun": 1.00,
    "kismen_uygun": 1.10,
    "uygun_degil": 1.20,
}

# Yük yönetimi yatırım sabiti
YATIRIM_SABITI_YK_TL_PER_KW = 600       # TL/kW

# Batarya yatırım sabiti
YATIRIM_SABITI_BAT_TL_PER_KWH = 9000    # TL/kWh

# Batarya kapasite sınırları
BATARYA_MIN_KWH = 60
BATARYA_MAX_KWH = 500

# Batarya süre sabitleri (mevcut/planlanan GES'e göre)
BATARYA_SURE = {
    "evet": 2,
    "hayir": 1,
}

# Kritik güç oranları
KRITIK_GUC_ORANLARI = {
    "dusuk": 0.05,
    "orta": 0.10,
    "yuksek": 0.20,
}

# Karmaşıklık tersi sabitleri
KARMASIKLIK_TERSI = {
    "EV": 60,
    "GES": 80,
    "YK": 70,
    "BAT": 50,
}

# Operasyonel uyum sabitleri
OPERASYONEL_UYUM = {
    "EV": 65,
    "GES": 85,
    "YK": 75,
    "BAT": 60,
}

# Kesinti uyum skorları
KESINTI_UYUMU = {
    "EV": {"dusuk": 40, "orta": 70, "yuksek": 100},
    "GES": {"dusuk": 85, "orta": 95, "yuksek": 100},
    "YK": {"dusuk": 60, "orta": 80, "yuksek": 100},
    "BAT": {"dusuk": 75, "orta": 90, "yuksek": 100},
}

# Veri yeterliliği sabiti
VERI_YETERLILIGI_SKORU = 100

# Yatırım türleri etiketi
YATIRIM_ETIKETLERI = {
    "EV": "Enerji Verimliliği",
    "GES": "Çatı GES",
    "YK": "Yük Yönetimi",
    "BAT": "Batarya Depolama",
}

# Örnek veri setleri – 3 gerçekçi OSB KOBİ senaryosu

ORNEK_VERI_1 = {
    # Örnek Veri 1: Dengeli KOBİ – ana demo senaryosu
    "aylik_tuketim_kwh": 120000,
    "aylik_fatura_tl": 540000,
    "maksimum_talep_kw": 420,
    "gunluk_calisma_saati": 10,
    "haftalik_calisma_gunu": 6,
    "gunduz_calisma_orani": 75,
    "faaliyet_gostergesi_turu": "adet",
    "aylik_faaliyet_miktari": 18000,
    "yatirim_butcesi_tl": 6000000,
    "uretim_kesintisi_toleransi": "orta",
    "basincli_hava_yogunlugu": "orta",
    "aydinlatma_sistem_yasi": "orta",
    "motor_surucu_onemi": "yuksek",
    "hvac_onemi": "dusuk",
    "yardimci_servis_belirginligi": "orta",
    "kullanilabilir_cati_alani_m2": 1800,
    "cati_uygunlugu": "uygun",
    "yuk_kaydirma_esnekligi": "orta",
    "pik_saatlerde_uretim_zorunlulugu": "orta",
    "kritik_yuk_hassasiyeti": "orta",
    "mevcut_veya_planlanan_ges": "evet",
}

ORNEK_VERI_2 = {
    # Örnek Veri 2: GES Uygun Tesis
    "aylik_tuketim_kwh": 95000,
    "aylik_fatura_tl": 430000,
    "maksimum_talep_kw": 300,
    "gunluk_calisma_saati": 9,
    "haftalik_calisma_gunu": 6,
    "gunduz_calisma_orani": 90,
    "faaliyet_gostergesi_turu": "adet",
    "aylik_faaliyet_miktari": 15000,
    "yatirim_butcesi_tl": 5500000,
    "uretim_kesintisi_toleransi": "orta",
    "basincli_hava_yogunlugu": "dusuk",
    "aydinlatma_sistem_yasi": "orta",
    "motor_surucu_onemi": "orta",
    "hvac_onemi": "dusuk",
    "yardimci_servis_belirginligi": "dusuk",
    "kullanilabilir_cati_alani_m2": 2400,
    "cati_uygunlugu": "uygun",
    "yuk_kaydirma_esnekligi": "orta",
    "pik_saatlerde_uretim_zorunlulugu": "dusuk",
    "kritik_yuk_hassasiyeti": "dusuk",
    "mevcut_veya_planlanan_ges": "hayir",
}

ORNEK_VERI_3 = {
    # Örnek Veri 3: Verimlilik Öncelikli Tesis
    "aylik_tuketim_kwh": 140000,
    "aylik_fatura_tl": 620000,
    "maksimum_talep_kw": 500,
    "gunluk_calisma_saati": 11,
    "haftalik_calisma_gunu": 6,
    "gunduz_calisma_orani": 60,
    "faaliyet_gostergesi_turu": "adet",
    "aylik_faaliyet_miktari": 22000,
    "yatirim_butcesi_tl": 6500000,
    "uretim_kesintisi_toleransi": "orta",
    "basincli_hava_yogunlugu": "yuksek",
    "aydinlatma_sistem_yasi": "eski",
    "motor_surucu_onemi": "yuksek",
    "hvac_onemi": "orta",
    "yardimci_servis_belirginligi": "yuksek",
    "kullanilabilir_cati_alani_m2": 900,
    "cati_uygunlugu": "kismen_uygun",
    "yuk_kaydirma_esnekligi": "orta",
    "pik_saatlerde_uretim_zorunlulugu": "yuksek",
    "kritik_yuk_hassasiyeti": "orta",
    "mevcut_veya_planlanan_ges": "hayir",
}

ORNEK_VERILER = {
    "1": ORNEK_VERI_1,
    "2": ORNEK_VERI_2,
    "3": ORNEK_VERI_3,
}


# ============================================================
# SKOR DÖNÜŞÜM FONKSİYONLARI
# ============================================================

def yogunluk_skor(deger: str) -> float:
    """Yoğunluk / önem / esneklik / hassasiyet dönüşümü (Bölüm 2.1)."""
    tablo = {"yok": 0, "dusuk": 25, "orta": 60, "yuksek": 100}
    return tablo[deger]


def uygunluk_skor(deger: str) -> float:
    """Uygunluk dönüşümü (Bölüm 2.2)."""
    tablo = {"uygun_degil": 0, "kismen_uygun": 50, "uygun": 100}
    return tablo[deger]


def sistem_yasi_skor(deger: str) -> float:
    """Sistem yaşı / verimsizlik fırsatı dönüşümü (Bölüm 2.3)."""
    tablo = {"yeni": 20, "orta": 60, "eski": 100}
    return tablo[deger]


def ikili_skor(deger: str) -> float:
    """İkili veri dönüşümü (Bölüm 2.4)."""
    tablo = {"hayir": 0, "evet": 100}
    return tablo[deger]


def kesinti_tolerans_skor(deger: str) -> float:
    """Üretim kesintisine tolerans dönüşümü (Bölüm 2.5)."""
    tablo = {"dusuk": 20, "orta": 60, "yuksek": 100}
    return tablo[deger]


# ============================================================
# BANT SKOR FONKSİYONLARI
# ============================================================

def aylik_tuketim_skoru(x: float) -> float:
    """Bölüm 3.1"""
    if x <= 50000:
        return 20
    elif x <= 150000:
        return 45
    elif x <= 300000:
        return 70
    else:
        return 100


def aylik_fatura_skoru(x: float) -> float:
    """Bölüm 3.2"""
    if x <= 250000:
        return 20
    elif x <= 750000:
        return 45
    elif x <= 1500000:
        return 70
    else:
        return 100


def maksimum_talep_skoru(x: float) -> float:
    """Bölüm 3.3"""
    if x <= 250:
        return 20
    elif x <= 750:
        return 45
    elif x <= 1500:
        return 70
    else:
        return 100


def gunluk_calisma_skoru(x: float) -> float:
    """Bölüm 3.4"""
    if x <= 8:
        return 30
    elif x <= 16:
        return 70
    else:
        return 100


def haftalik_calisma_skoru(x: float) -> float:
    """Bölüm 3.5"""
    if x <= 3:
        return 20
    elif x <= 5:
        return 60
    else:
        return 100


def gunduz_calisma_skoru(x: float) -> float:
    """Bölüm 3.6"""
    if x <= 20:
        return 10
    elif x <= 40:
        return 30
    elif x <= 60:
        return 55
    elif x <= 80:
        return 80
    else:
        return 100


def cati_alani_skoru(x: float) -> float:
    """Bölüm 3.7"""
    if x <= 200:
        return 20
    elif x <= 500:
        return 45
    elif x <= 1000:
        return 70
    else:
        return 100


def geri_odeme_skoru(x: float) -> float:
    """Bölüm 8.3 – Geri ödeme süresi skoru."""
    if x <= 2:
        return 100
    elif x <= 3:
        return 85
    elif x <= 5:
        return 65
    elif x <= 7:
        return 40
    else:
        return 15


def butce_uyum_skoru(butce: float, yatirim: float) -> float:
    """Bölüm 8.5 – Bütçe uyum skoru."""
    if yatirim == 0:
        return 100
    oran = butce / yatirim
    if oran >= 1.00:
        return 100
    elif oran >= 0.80:
        return 80
    elif oran >= 0.60:
        return 55
    elif oran >= 0.40:
        return 30
    else:
        return 10


def cevresel_etki_bant_skoru(etki_orani: float) -> float:
    """Çevresel etki bant puanı – yıllık enerji azaltımının yıllık tüketime oranına göre."""
    if etki_orani < 0.05:
        return 10
    elif etki_orani < 0.10:
        return 25
    elif etki_orani < 0.20:
        return 45
    elif etki_orani < 0.35:
        return 65
    elif etki_orani < 0.50:
        return 80
    else:
        return 95


# ============================================================
# ANA HESAPLAMA MOTORU
# ============================================================

def hesapla(v: dict) -> dict:
    """
    Tüm deterministik hesaplamayı yapar.
    v: kullanıcı girdileri sözlüğü.
    Dönen: tüm ara ve nihai sonuçları içeren sözlük.
    """
    r = {}

    # ------ Kategorik skorlama ------
    skor_basincli_hava = yogunluk_skor(v["basincli_hava_yogunlugu"])
    skor_aydinlatma = sistem_yasi_skor(v["aydinlatma_sistem_yasi"])
    skor_motor = yogunluk_skor(v["motor_surucu_onemi"])
    skor_hvac = yogunluk_skor(v["hvac_onemi"])
    skor_yardimci = yogunluk_skor(v["yardimci_servis_belirginligi"])
    skor_cati_uyg = uygunluk_skor(v["cati_uygunlugu"])
    skor_yuk_esn = yogunluk_skor(v["yuk_kaydirma_esnekligi"])
    skor_pik = yogunluk_skor(v["pik_saatlerde_uretim_zorunlulugu"])
    skor_kritik_yuk = yogunluk_skor(v["kritik_yuk_hassasiyeti"])
    skor_ges_mevcut = ikili_skor(v["mevcut_veya_planlanan_ges"])

    # ------ Bant skorlaması ------
    s_tuketim = aylik_tuketim_skoru(v["aylik_tuketim_kwh"])
    s_fatura = aylik_fatura_skoru(v["aylik_fatura_tl"])
    s_talep = maksimum_talep_skoru(v["maksimum_talep_kw"])
    s_gunluk = gunluk_calisma_skoru(v["gunluk_calisma_saati"])
    s_haftalik = haftalik_calisma_skoru(v["haftalik_calisma_gunu"])
    s_gunduz = gunduz_calisma_skoru(v["gunduz_calisma_orani"])
    s_cati_alan = cati_alani_skoru(v["kullanilabilir_cati_alani_m2"])

    # ------ Ara hesaplamalar ------
    birim_enerji_maliyeti = (
        v["aylik_fatura_tl"] / v["aylik_tuketim_kwh"]
        if v["aylik_tuketim_kwh"] > 0
        else 0
    )
    r["birim_enerji_maliyeti"] = birim_enerji_maliyeti

    yillik_tuketim = 12 * v["aylik_tuketim_kwh"]
    yillik_fatura = 12 * v["aylik_fatura_tl"]
    r["yillik_tuketim"] = yillik_tuketim
    r["yillik_fatura"] = yillik_fatura

    # EV fırsat skoru
    ev_firsat = (
        skor_basincli_hava + skor_aydinlatma + skor_motor + skor_hvac + skor_yardimci
    ) / 5
    r["ev_firsat"] = ev_firsat

    # ------ GES boyutlandırma (düzeltilmiş) ------
    # Öz tüketim hedefi: gündüz oranına göre 0.35–0.65
    oz_tuketim_hedefi = 0.35 + 0.003 * v["gunduz_calisma_orani"]
    r["oz_tuketim_hedefi"] = oz_tuketim_hedefi

    # İhtiyaca göre PV boyutlandırma
    pv_ihtiyac = (
        (yillik_tuketim * oz_tuketim_hedefi) / YILLIK_GES_URETIM_SABITI
        if YILLIK_GES_URETIM_SABITI > 0
        else 0
    )
    pv_cati_max = v["kullanilabilir_cati_alani_m2"] / PV_M2_PER_KWP
    pv_kwp = min(pv_ihtiyac, pv_cati_max)
    r["pv_ihtiyac"] = pv_ihtiyac
    r["pv_cati_max"] = pv_cati_max
    r["pv_kwp"] = pv_kwp

    # GES yıllık üretim
    yillik_uretim_ges = pv_kwp * YILLIK_GES_URETIM_SABITI
    r["yillik_uretim_ges"] = yillik_uretim_ges

    # GES faydalı enerji – %90 yıllık tüketim üst sınırı
    faydali_enerji_ges_ham = yillik_uretim_ges * oz_tuketim_hedefi
    faydali_enerji_ges = min(faydali_enerji_ges_ham, 0.90 * yillik_tuketim)
    r["faydali_enerji_ges"] = faydali_enerji_ges

    # Eski uyumlu öz tüketim çarpanı (teknik uygunluk alt kriteri için kullanılır)
    oz_tuketim_carpani = oz_tuketim_hedefi
    r["oz_tuketim_carpani"] = oz_tuketim_carpani

    # ------ Batarya boyutlandırma (düzeltilmiş) ------
    kritik_guc_orani = KRITIK_GUC_ORANLARI[v["kritik_yuk_hassasiyeti"]]
    kritik_guc_kw = v["maksimum_talep_kw"] * kritik_guc_orani
    batarya_sure = BATARYA_SURE[v["mevcut_veya_planlanan_ges"]]
    batarya_kapasitesi_kwh_ham = kritik_guc_kw * batarya_sure
    batarya_kapasitesi_kwh = min(max(batarya_kapasitesi_kwh_ham, BATARYA_MIN_KWH), BATARYA_MAX_KWH)
    r["kritik_guc_kw"] = kritik_guc_kw
    r["batarya_sure"] = batarya_sure
    r["batarya_kapasitesi_kwh"] = batarya_kapasitesi_kwh

    # ------ Yıllık tasarruf hesapları ------

    # EV tasarrufu
    tasarruf_orani_ev = 0.05 + 0.15 * (ev_firsat / 100)
    yillik_tasarruf_ev = yillik_fatura * tasarruf_orani_ev
    r["tasarruf_orani_ev"] = tasarruf_orani_ev
    r["yillik_tasarruf_ev"] = yillik_tasarruf_ev

    # GES tasarrufu (düzeltilmiş)
    yillik_tasarruf_ges = faydali_enerji_ges * birim_enerji_maliyeti
    r["yillik_tasarruf_ges"] = yillik_tasarruf_ges

    # YK tasarrufu
    yk_pot = (
        0.50 * skor_yuk_esn
        + 0.30 * (100 - skor_pik)
        + 0.20 * s_talep
    )
    tasarruf_orani_yk = 0.02 + 0.08 * (yk_pot / 100)
    yillik_tasarruf_yk = yillik_fatura * tasarruf_orani_yk
    r["yk_pot"] = yk_pot
    r["tasarruf_orani_yk"] = tasarruf_orani_yk
    r["yillik_tasarruf_yk"] = yillik_tasarruf_yk

    # BAT tasarrufu
    bat_pot = (
        0.40 * skor_kritik_yuk
        + 0.30 * skor_ges_mevcut
        + 0.30 * s_talep
    )
    tasarruf_orani_bat = 0.01 + 0.07 * (bat_pot / 100)
    yillik_tasarruf_bat = yillik_fatura * tasarruf_orani_bat
    r["bat_pot"] = bat_pot
    r["tasarruf_orani_bat"] = tasarruf_orani_bat
    r["yillik_tasarruf_bat"] = yillik_tasarruf_bat

    # ------ Yatırım maliyetleri (düzeltilmiş) ------
    # EV: yıllık fatura × (0.10 + 0.20 × EV_firsat/100)
    yatirim_ev = yillik_fatura * (0.10 + 0.20 * ev_firsat / 100)

    # GES: PV × 18000 × çatı uygunluk çarpanı, bütçenin %70'ini aşamaz
    cati_carpani = CATI_UYGUNLUK_CARPANI[v["cati_uygunlugu"]]
    yatirim_ges_ham = pv_kwp * YATIRIM_SABITI_GES_TL_PER_KWP * cati_carpani
    yatirim_ges = min(yatirim_ges_ham, 0.70 * v["yatirim_butcesi_tl"])

    # YK: değişmedi
    yatirim_yk = v["maksimum_talep_kw"] * YATIRIM_SABITI_YK_TL_PER_KW

    # BAT: 9000 TL/kWh
    yatirim_bat = batarya_kapasitesi_kwh * YATIRIM_SABITI_BAT_TL_PER_KWH

    r["yatirim"] = {"EV": yatirim_ev, "GES": yatirim_ges, "YK": yatirim_yk, "BAT": yatirim_bat}

    # ------ Geri ödeme (Bölüm 8.2) ------
    def safe_payback(yat, tas):
        return yat / tas if tas > 0 else 999

    geri_odeme = {
        "EV": safe_payback(yatirim_ev, yillik_tasarruf_ev),
        "GES": safe_payback(yatirim_ges, yillik_tasarruf_ges),
        "YK": safe_payback(yatirim_yk, yillik_tasarruf_yk),
        "BAT": safe_payback(yatirim_bat, yillik_tasarruf_bat),
    }
    r["geri_odeme"] = geri_odeme

    # Geri ödeme skorları (Bölüm 8.3)
    geri_odeme_skorlari = {k: geri_odeme_skoru(val) for k, val in geri_odeme.items()}
    r["geri_odeme_skorlari"] = geri_odeme_skorlari

    # ------ Tasarruf skoru (Bölüm 8.4) ------
    tasarruflar = {
        "EV": yillik_tasarruf_ev,
        "GES": yillik_tasarruf_ges,
        "YK": yillik_tasarruf_yk,
        "BAT": yillik_tasarruf_bat,
    }
    max_tasarruf = max(tasarruflar.values())
    tasarruf_skorlari = {}
    for k, val in tasarruflar.items():
        tasarruf_skorlari[k] = (100 * val / max_tasarruf) if max_tasarruf > 0 else 0
    r["yillik_tasarruflar"] = tasarruflar
    r["tasarruf_skorlari"] = tasarruf_skorlari

    # ------ Bütçe uyum skorları (Bölüm 8.5) ------
    butce_uyum = {
        k: butce_uyum_skoru(v["yatirim_butcesi_tl"], yat)
        for k, yat in r["yatirim"].items()
    }
    r["butce_uyum"] = butce_uyum

    # ====== ANA KRİTER SKORLARI (Bölüm 9) ======

    # 9.1 Ekonomik çekicilik
    E = {}
    for j in ["EV", "GES", "YK", "BAT"]:
        E[j] = (
            0.40 * tasarruf_skorlari[j]
            + 0.35 * geri_odeme_skorlari[j]
            + 0.25 * butce_uyum[j]
        )
    r["E"] = E

    # 9.2 Teknik uygunluk
    T = {}
    T["EV"] = (
        0.20 * skor_basincli_hava
        + 0.20 * skor_aydinlatma
        + 0.20 * skor_motor
        + 0.20 * skor_hvac
        + 0.20 * skor_yardimci
    )
    T["GES"] = (
        0.45 * skor_cati_uyg
        + 0.35 * s_cati_alan
        + 0.20 * s_gunduz
    )
    T["YK"] = (
        0.50 * skor_yuk_esn
        + 0.30 * (100 - skor_pik)
        + 0.20 * s_gunluk
    )
    T["BAT"] = (
        0.45 * skor_kritik_yuk
        + 0.30 * skor_ges_mevcut
        + 0.25 * s_talep
    )
    r["T"] = T

    # 9.3 Performans iyileştirme potansiyeli
    P = {}
    P["EV"] = 0.40 * ev_firsat + 0.30 * s_tuketim + 0.30 * s_gunluk
    P["GES"] = 0.40 * s_gunduz + 0.35 * s_cati_alan + 0.25 * s_tuketim
    P["YK"] = 0.45 * skor_yuk_esn + 0.35 * s_talep + 0.20 * skor_pik
    P["BAT"] = 0.35 * skor_kritik_yuk + 0.35 * s_talep + 0.30 * skor_ges_mevcut
    r["P"] = P

    # 9.4 Uygulanabilirlik
    tolerans = v["uretim_kesintisi_toleransi"]
    U = {}
    for j in ["EV", "GES", "YK", "BAT"]:
        kesinti_u = KESINTI_UYUMU[j][tolerans]
        karmasiklik_t = KARMASIKLIK_TERSI[j]
        operasyonel_u = OPERASYONEL_UYUM[j]
        U[j] = (
            0.35 * kesinti_u
            + 0.25 * karmasiklik_t
            + 0.20 * VERI_YETERLILIGI_SKORU
            + 0.20 * operasyonel_u
        )
    r["U"] = U

    # 9.5 Çevresel etki – oran tabanlı bant puanlaması
    yillik_enerji_azaltimi = {}
    yillik_enerji_azaltimi["EV"] = (
        yillik_tasarruf_ev / birim_enerji_maliyeti if birim_enerji_maliyeti > 0 else 0
    )
    yillik_enerji_azaltimi["GES"] = faydali_enerji_ges
    yillik_enerji_azaltimi["YK"] = (
        yillik_tasarruf_yk / birim_enerji_maliyeti if birim_enerji_maliyeti > 0 else 0
    )
    yillik_enerji_azaltimi["BAT"] = (
        yillik_tasarruf_bat / birim_enerji_maliyeti if birim_enerji_maliyeti > 0 else 0
    )

    etki_oranlari = {}
    C = {}
    for j in ["EV", "GES", "YK", "BAT"]:
        etki_orani = (
            yillik_enerji_azaltimi[j] / yillik_tuketim if yillik_tuketim > 0 else 0
        )
        etki_oranlari[j] = etki_orani
        C[j] = cevresel_etki_bant_skoru(etki_orani)
    r["yillik_enerji_azaltimi"] = yillik_enerji_azaltimi
    r["etki_oranlari"] = etki_oranlari
    r["C"] = C

    # ====== NİHAİ TOPLAM SKOR (Bölüm 10) ======
    toplam = {}
    for j in ["EV", "GES", "YK", "BAT"]:
        toplam[j] = (
            KRITER_AGIRLIKLARI["ekonomik_cekicilik"] * E[j]
            + KRITER_AGIRLIKLARI["teknik_uygunluk"] * T[j]
            + KRITER_AGIRLIKLARI["performans_iyilestirme_potansiyeli"] * P[j]
            + KRITER_AGIRLIKLARI["uygulanabilirlik"] * U[j]
            + KRITER_AGIRLIKLARI["cevresel_etki"] * C[j]
        )
    r["toplam"] = toplam

    # Sıralama
    siralama = sorted(toplam.items(), key=lambda x: x[1], reverse=True)
    oncelik = {}
    for idx, (key, _) in enumerate(siralama, 1):
        oncelik[key] = idx
    r["oncelik"] = oncelik
    r["siralama"] = siralama

    return r


# ============================================================
# AÇIKLAMA METNİ ÜRETİCİSİ
# ============================================================

def aciklama_uret(v: dict, r: dict) -> str:
    """
    Bölüm 13: Sadece hesaplanmış skorlara ve giriş verilerine dayanan
    deterministik açıklama metni üretir. Yeni katsayı, içgörü veya
    tahmin eklemez.
    """
    siralama = r["siralama"]
    birinci_kod = siralama[0][0]
    birinci_ad = YATIRIM_ETIKETLERI[birinci_kod]
    birinci_skor = siralama[0][1]
    sonuncu_kod = siralama[-1][0]
    sonuncu_ad = YATIRIM_ETIKETLERI[sonuncu_kod]
    sonuncu_skor = siralama[-1][1]

    # En yüksek kriter skorunu bul (birinci için)
    kriter_adlari = {
        "E": "ekonomik çekicilik",
        "T": "teknik uygunluk",
        "P": "performans iyileştirme potansiyeli",
        "U": "uygulanabilirlik",
        "C": "çevresel etki",
    }
    kriter_skorlari_birinci = {
        k: r[k][birinci_kod] for k in ["E", "T", "P", "U", "C"]
    }
    en_yuksek_kriter = max(kriter_skorlari_birinci, key=kriter_skorlari_birinci.get)

    # Sonuncunun en düşük kriter skoru
    kriter_skorlari_sonuncu = {
        k: r[k][sonuncu_kod] for k in ["E", "T", "P", "U", "C"]
    }
    en_dusuk_kriter = min(kriter_skorlari_sonuncu, key=kriter_skorlari_sonuncu.get)

    metin = (
        f"Analiz sonucuna göre {birinci_ad} seçeneği {birinci_skor:.1f} puanla "
        f"en yüksek önceliğe sahiptir. "
        f"Bu seçeneğin öne çıkmasında {kriter_adlari[en_yuksek_kriter]} kriteri "
        f"({kriter_skorlari_birinci[en_yuksek_kriter]:.1f} puan) belirleyici olmuştur. "
        f"{sonuncu_ad} seçeneği ise {sonuncu_skor:.1f} puanla son sırada yer almaktadır; "
        f"bunun başlıca nedeni {kriter_adlari[en_dusuk_kriter]} kriterindeki "
        f"düşük performanstır ({kriter_skorlari_sonuncu[en_dusuk_kriter]:.1f} puan). "
        f"Girilen aylık tüketim ({v['aylik_tuketim_kwh']:,.0f} kWh) ve "
        f"fatura ({v['aylik_fatura_tl']:,.0f} TL) değerleri tüm skorları doğrudan etkilemiştir. "
        f"Bu çıktı ön fizibilite niteliğinde olup detaylı mühendislik analizinin yerine geçmez."
    )
    return metin


# ============================================================
# YARDIMCI FORMATLAMA FONKSİYONLARI
# ============================================================

def format_tl(val: float) -> str:
    """TL para formatı."""
    return f"₺{val:,.0f}"


def format_kwh(val: float) -> str:
    return f"{val:,.0f} kWh"


def format_yil(val: float) -> str:
    if val >= 999:
        return "—"
    return f"{val:.1f} yıl"


# ============================================================
# EXCEL ÇIKTI FONKSİYONU
# ============================================================

def durum_etiketi(toplam_skor: float, geri_odeme: float) -> str:
    """Ön fizibilite durum etiketi üretir. Deterministik kural."""
    if toplam_skor >= 75 and geri_odeme <= 4:
        return "Güçlü öncelik"
    elif toplam_skor >= 60:
        return "Değerlendirilmeli"
    else:
        return "İkinci aşama adayı"


def excel_olustur(veri: dict, sonuc: dict) -> BytesIO:
    """
    Sonuçları 4 sayfalı Excel dosyası olarak oluşturur.
    Sayfa 1: Girdi Verileri
    Sayfa 2: Sonuç Özeti
    Sayfa 3: Ön Fizibilite Özeti
    Sayfa 4: Teknik ve Ekonomik Detaylar
    """
    output = BytesIO()

    # Girdi etiketleri
    girdi_etiketleri = {
        "aylik_tuketim_kwh": ("Aylık Tüketim", "kWh/ay"),
        "aylik_fatura_tl": ("Aylık Fatura", "TL/ay"),
        "maksimum_talep_kw": ("Maksimum Talep", "kW"),
        "gunluk_calisma_saati": ("Günlük Çalışma Saati", "saat"),
        "haftalik_calisma_gunu": ("Haftalık Çalışma Günü", "gün"),
        "gunduz_calisma_orani": ("Gündüz Çalışma Oranı", "%"),
        "faaliyet_gostergesi_turu": ("Faaliyet Göstergesi Türü", "kategori"),
        "aylik_faaliyet_miktari": ("Aylık Faaliyet Miktarı", "birim"),
        "yatirim_butcesi_tl": ("Yatırım Bütçesi", "TL"),
        "uretim_kesintisi_toleransi": ("Üretim Kesintisi Toleransı", "kategori"),
        "basincli_hava_yogunlugu": ("Basınçlı Hava Yoğunluğu", "kategori"),
        "aydinlatma_sistem_yasi": ("Aydınlatma Sistem Yaşı", "kategori"),
        "motor_surucu_onemi": ("Motor Sürücü Önemi", "kategori"),
        "hvac_onemi": ("HVAC Önemi", "kategori"),
        "yardimci_servis_belirginligi": ("Yardımcı Servis Belirginliği", "kategori"),
        "kullanilabilir_cati_alani_m2": ("Kullanılabilir Çatı Alanı", "m²"),
        "cati_uygunlugu": ("Çatı Uygunluğu", "kategori"),
        "yuk_kaydirma_esnekligi": ("Yük Kaydırma Esnekliği", "kategori"),
        "pik_saatlerde_uretim_zorunlulugu": ("Pik Saatlerde Üretim Zorunluluğu", "kategori"),
        "kritik_yuk_hassasiyeti": ("Kritik Yük Hassasiyeti", "kategori"),
        "mevcut_veya_planlanan_ges": ("Mevcut veya Planlanan GES", "kategori"),
    }

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Sayfa 1: Girdi Verileri
        girdi_rows = []
        for key, (label, birim) in girdi_etiketleri.items():
            girdi_rows.append({
                "Alan Adı": label,
                "Değer": veri.get(key, ""),
                "Birim / Kategori": birim,
            })
        df_girdi = pd.DataFrame(girdi_rows)
        df_girdi.to_excel(writer, sheet_name="Girdi Verileri", index=False)

        # Sayfa 2: Sonuç Özeti
        sonuc_rows = []
        for kod, _ in sonuc["siralama"]:
            sonuc_rows.append({
                "Yatırım Adı": YATIRIM_ETIKETLERI[kod],
                "Öncelik Sırası": sonuc["oncelik"][kod],
                "Toplam Skor": round(sonuc["toplam"][kod], 2),
                "Ekonomik Çekicilik": round(sonuc["E"][kod], 2),
                "Teknik Uygunluk": round(sonuc["T"][kod], 2),
                "Performans İyileştirme Potansiyeli": round(sonuc["P"][kod], 2),
                "Uygulanabilirlik": round(sonuc["U"][kod], 2),
                "Çevresel Etki": round(sonuc["C"][kod], 2),
            })
        df_sonuc = pd.DataFrame(sonuc_rows)
        df_sonuc.to_excel(writer, sheet_name="Sonuç Özeti", index=False)

        # Sayfa 3: Ön Fizibilite Özeti
        fizibilite_rows = []
        for kod, _ in sonuc["siralama"]:
            go_val = sonuc["geri_odeme"][kod]
            fizibilite_rows.append({
                "Yatırım Adı": YATIRIM_ETIKETLERI[kod],
                "Tahmini Yatırım Maliyeti (TL)": round(sonuc["yatirim"][kod], 0),
                "Tahmini Yıllık Tasarruf (TL)": round(sonuc["yillik_tasarruflar"][kod], 0),
                "Basit Geri Ödeme Süresi (yıl)": round(go_val, 2) if go_val < 999 else "—",
                "Durum Etiketi": durum_etiketi(sonuc["toplam"][kod], go_val),
            })
        df_fizibilite = pd.DataFrame(fizibilite_rows)
        df_fizibilite.to_excel(writer, sheet_name="Ön Fizibilite Özeti", index=False)

        # Sayfa 4: Teknik ve Ekonomik Detaylar
        detay_rows = []
        for kod, _ in sonuc["siralama"]:
            detay_rows.append({
                "Yatırım Adı": YATIRIM_ETIKETLERI[kod],
                "Tasarruf Skoru": round(sonuc["tasarruf_skorlari"][kod], 2),
                "Geri Ödeme Skoru": round(sonuc["geri_odeme_skorlari"][kod], 2),
                "Bütçe Uyumu Skoru": round(sonuc["butce_uyum"][kod], 2),
                "Yıllık Enerji Azaltımı (kWh)": round(sonuc["yillik_enerji_azaltimi"][kod], 0),
                "Etki Oranı": round(sonuc["etki_oranlari"][kod], 4),
            })
        df_detay = pd.DataFrame(detay_rows)
        df_detay.to_excel(writer, sheet_name="Teknik ve Ekonomik", index=False)

    output.seek(0)
    return output


# ============================================================
# STREAMLIT ARAYÜZÜ
# ============================================================

# Yatırım tipi ikonları
YATIRIM_IKONLARI = {
    "EV": "⚡",
    "GES": "☀️",
    "YK": "⏱️",
    "BAT": "🔋",
}


def main():
    st.set_page_config(
        page_title="EN²TECH Enerji Pusulası",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # ===================== CUSTOM CSS =====================
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

        /* ==================== ROOT VARIABLES ==================== */
        :root {
            --primary-dark: #0E2E5C;
            --primary: #1F5FBF;
            --primary-mid: #2E73D8;
            --turquoise: #37B5E5;
            --green: #00C16A;
            --bg-light: #EEF3FA;
            --white: #FFFFFF;
            --text-dark: #0E2E5C;
            --text-secondary: #1D3557;
            --text-muted: #4A6B8A;
            --border-light: #D4E0F0;
            --card-shadow: 0 2px 12px rgba(14,46,92,0.07);
        }

        /* ==================== GLOBAL STYLES ==================== */
        .stApp {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-light);
        }

        /* Force all standard text to be dark and visible */
        .stApp, .stApp p, .stApp span, .stApp div, .stApp label {
            color: var(--text-dark);
        }
        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
            color: var(--text-dark);
        }

        /* ==================== HERO SECTION ==================== */
        .hero-section {
            background: linear-gradient(135deg, #0E2E5C 0%, #1F5FBF 50%, #2E73D8 100%);
            padding: 2.8rem 2.5rem 2.5rem 2.5rem;
            border-radius: 0 0 24px 24px;
            margin: -1rem -1rem 2rem -1rem;
            position: relative;
            overflow: hidden;
        }
        .hero-section::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background:
                radial-gradient(circle at 85% 25%, rgba(55,181,229,0.15) 0%, transparent 50%),
                radial-gradient(circle at 15% 75%, rgba(0,193,106,0.08) 0%, transparent 40%);
            pointer-events: none;
        }
        .hero-section::after {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background-image:
                linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
            background-size: 40px 40px;
            pointer-events: none;
        }
        .hero-content { position: relative; z-index: 2; }
        .hero-badge {
            display: inline-block;
            background: rgba(55,181,229,0.2);
            border: 1px solid rgba(55,181,229,0.4);
            color: #a8e0f5;
            padding: 0.3rem 1rem;
            border-radius: 20px;
            font-size: 0.78rem;
            font-weight: 600;
            letter-spacing: 0.5px;
            margin-bottom: 1rem;
        }
        .hero-title {
            font-size: 2.6rem;
            font-weight: 900;
            color: #FFFFFF;
            margin: 0 0 0.4rem 0;
            letter-spacing: -1px;
            line-height: 1.1;
        }
        .hero-title span {
            background: linear-gradient(90deg, #37B5E5, #00C16A);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .hero-subtitle {
            font-size: 1.05rem;
            color: rgba(255,255,255,0.9);
            margin: 0.6rem 0 0.3rem 0;
            line-height: 1.5;
            max-width: 680px;
        }
        .hero-subtitle-2 {
            font-size: 0.92rem;
            color: #a8e0f5;
            font-weight: 500;
            margin: 0;
            font-style: italic;
        }
        .hero-icons {
            display: flex;
            gap: 1rem;
            margin-top: 1.5rem;
            flex-wrap: wrap;
        }
        .hero-icon-box {
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 12px;
            padding: 0.8rem 1.2rem;
            text-align: center;
            color: #FFFFFF;
            font-size: 0.78rem;
            font-weight: 500;
            min-width: 90px;
            backdrop-filter: blur(4px);
        }
        .hero-icon-box .icon { font-size: 1.5rem; display: block; margin-bottom: 0.3rem; }

        /* ==================== NOTICE BANNER ==================== */
        .notice-banner {
            background: linear-gradient(135deg, #FFFBF0, #FFF7E6);
            border: 1px solid #F0D78C;
            border-left: 4px solid #E8B830;
            padding: 0.85rem 1.2rem;
            border-radius: 10px;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }
        .notice-banner .n-icon { font-size: 1.1rem; }
        .notice-banner .n-text { font-size: 0.85rem; color: #5C4A10; line-height: 1.4; font-weight: 500; }
        .notice-banner .n-text strong { color: #3D3008; }

        /* ==================== SECTION HEADERS ==================== */
        .section-header {
            display: flex;
            align-items: center;
            gap: 0.6rem;
            margin: 2rem 0 1rem 0;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid var(--border-light);
        }
        .section-header .dot {
            width: 8px; height: 8px;
            background: var(--turquoise);
            border-radius: 50%;
            flex-shrink: 0;
        }
        .section-header h2 {
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--text-dark);
            margin: 0;
        }

        /* ==================== EXPANDER CARDS ==================== */
        div[data-testid="stExpander"] {
            background: var(--white);
            border: 1px solid var(--border-light);
            border-radius: 14px;
            margin-bottom: 0.7rem;
            box-shadow: var(--card-shadow);
            overflow: hidden;
        }
        div[data-testid="stExpander"] > details > summary {
            font-weight: 600;
            color: var(--primary) !important;
            font-size: 0.95rem;
        }
        div[data-testid="stExpander"] > details > summary span {
            color: var(--primary) !important;
        }

        /* ==================== SUMMARY PANEL ==================== */
        .summary-panel {
            background: linear-gradient(135deg, var(--primary-dark), var(--primary));
            border-radius: 14px;
            padding: 1.2rem 1.5rem;
            color: #FFFFFF;
            margin-bottom: 1rem;
        }
        .summary-panel h3 {
            font-size: 0.85rem; font-weight: 600;
            color: rgba(255,255,255,0.75);
            text-transform: uppercase; letter-spacing: 1px;
            margin: 0 0 0.8rem 0;
        }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 0.8rem;
        }
        .summary-item { text-align: center; }
        .summary-item .val {
            font-size: 1.15rem;
            font-weight: 700;
            color: #FFFFFF;
        }
        .summary-item .lbl {
            font-size: 0.72rem;
            color: rgba(255,255,255,0.65);
            margin-top: 0.15rem;
        }

        /* ==================== RESULTS BANNER ==================== */
        .results-banner {
            background: linear-gradient(135deg, var(--primary-dark), var(--primary-mid));
            padding: 1.5rem 2rem;
            border-radius: 16px;
            margin: 2rem 0 1.5rem 0;
            text-align: center;
            position: relative;
            overflow: hidden;
        }
        .results-banner::before {
            content: '';
            position: absolute; top: 0; left: 0; right: 0; bottom: 0;
            background: radial-gradient(circle at 80% 50%, rgba(55,181,229,0.12) 0%, transparent 50%);
            pointer-events: none;
        }
        .results-banner h2 {
            font-size: 1.5rem; font-weight: 800;
            color: #FFFFFF; margin: 0 0 0.3rem 0;
            position: relative; z-index: 2;
        }
        .results-banner p {
            font-size: 0.88rem;
            color: rgba(255,255,255,0.8);
            margin: 0; position: relative; z-index: 2;
        }

        /* ==================== INVESTMENT CARDS ==================== */
        .inv-card {
            background: var(--white);
            border-radius: 16px;
            padding: 1.4rem 1.6rem;
            border: 1px solid var(--border-light);
            box-shadow: var(--card-shadow);
            margin-bottom: 1rem;
            transition: box-shadow 0.2s ease;
        }
        .inv-card:hover { box-shadow: 0 4px 20px rgba(14,46,92,0.1); }
        .inv-card.rank-1-card {
            border: 2px solid var(--turquoise);
            box-shadow: 0 4px 20px rgba(55,181,229,0.15);
        }
        .inv-card-header {
            display: flex; align-items: center;
            gap: 0.7rem; margin-bottom: 1rem;
        }
        .inv-rank {
            width: 40px; height: 40px; border-radius: 10px;
            display: flex; align-items: center; justify-content: center;
            font-size: 1.1rem; font-weight: 800;
            color: #FFFFFF; flex-shrink: 0;
        }
        .inv-rank.r1 { background: linear-gradient(135deg, #37B5E5, #00C16A); }
        .inv-rank.r2 { background: linear-gradient(135deg, #2E73D8, #1F5FBF); }
        .inv-rank.r3 { background: linear-gradient(135deg, #5A7BA6, #3D5F8A); }
        .inv-rank.r4 { background: linear-gradient(135deg, #8899AA, #6B7D8D); }
        .inv-icon { font-size: 1.4rem; }
        .inv-name {
            font-size: 1.1rem; font-weight: 700;
            color: var(--text-dark);
        }
        .inv-score {
            margin-left: auto; font-size: 1.6rem;
            font-weight: 800; color: var(--primary);
        }
        .inv-score.top { color: var(--turquoise); }
        .inv-metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 0.5rem;
        }
        .inv-metric {
            background: var(--bg-light);
            padding: 0.6rem 0.8rem;
            border-radius: 10px;
            text-align: center;
        }
        .inv-metric .m-label {
            font-size: 0.7rem;
            color: var(--text-muted);
            font-weight: 600;
            margin-bottom: 0.15rem;
        }
        .inv-metric .m-value {
            font-size: 1rem;
            font-weight: 700;
            color: var(--text-dark);
        }

        /* ==================== CHART CARDS ==================== */
        .chart-card {
            background: var(--white);
            border-radius: 16px;
            padding: 1.5rem;
            border: 1px solid var(--border-light);
            box-shadow: var(--card-shadow);
            margin-bottom: 1rem;
        }
        .chart-card-title {
            font-size: 1rem; font-weight: 700;
            color: var(--text-dark);
            margin-bottom: 0.8rem;
            display: flex; align-items: center; gap: 0.4rem;
        }

        /* ==================== EXPLANATION CARD ==================== */
        .explanation-card {
            background: var(--white);
            border-radius: 16px;
            padding: 1.5rem 1.8rem;
            border: 1px solid var(--border-light);
            box-shadow: var(--card-shadow);
            line-height: 1.7;
            color: var(--text-dark);
            font-size: 0.92rem;
        }
        .explanation-card .exp-title {
            font-size: 1rem; font-weight: 700;
            color: var(--primary);
            margin-bottom: 0.6rem;
            display: flex; align-items: center; gap: 0.4rem;
        }

        /* ==================== FOOTER ==================== */
        .ep-footer {
            text-align: center;
            padding: 2rem 0 1rem 0;
            color: var(--text-muted);
            font-size: 0.8rem;
        }
        .ep-footer strong { color: var(--primary); }

        /* ==================== BUTTON OVERRIDES ==================== */
        .stButton > button[kind="primary"],
        .stButton > button[data-testid="stBaseButton-primary"] {
            background: linear-gradient(135deg, var(--turquoise), #2AA3D0) !important;
            border: none !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
            font-size: 1rem !important;
            padding: 0.7rem 1.5rem !important;
            color: #FFFFFF !important;
            transition: all 0.2s ease !important;
        }
        .stButton > button[kind="primary"]:hover,
        .stButton > button[data-testid="stBaseButton-primary"]:hover {
            background: linear-gradient(135deg, #2AA3D0, var(--primary-mid)) !important;
            box-shadow: 0 4px 16px rgba(55,181,229,0.3) !important;
            color: #FFFFFF !important;
        }
        .stButton > button {
            color: var(--text-dark) !important;
        }

        /* ==================== DOWNLOAD BUTTON ==================== */
        .stDownloadButton > button {
            background: linear-gradient(135deg, #00C16A, #00A85A) !important;
            border: none !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
            color: #FFFFFF !important;
            padding: 0.6rem 1.2rem !important;
        }
        .stDownloadButton > button:hover {
            background: linear-gradient(135deg, #00A85A, #008F4C) !important;
            box-shadow: 0 4px 16px rgba(0,193,106,0.3) !important;
            color: #FFFFFF !important;
        }

        /* ==================== FORM VISIBILITY FIXES ==================== */
        /* Slider labels */
        .stSlider label, .stSlider p {
            color: var(--text-dark) !important;
        }
        /* Number input labels */
        .stNumberInput label, .stNumberInput p {
            color: var(--text-dark) !important;
        }
        /* Selectbox labels */
        .stSelectbox label, .stSelectbox p {
            color: var(--text-dark) !important;
        }
        /* Metric elements */
        [data-testid="stMetricLabel"] {
            color: var(--text-dark) !important;
        }
        [data-testid="stMetricValue"] {
            color: var(--text-dark) !important;
        }
        /* Expander text */
        div[data-testid="stExpander"] p,
        div[data-testid="stExpander"] span,
        div[data-testid="stExpander"] label {
            color: var(--text-dark) !important;
        }
        /* Markdown text inside expanders */
        div[data-testid="stExpander"] .stMarkdown p {
            color: var(--text-dark) !important;
        }
        /* Dataframe / table text */
        .stDataFrame, .stDataFrame td, .stDataFrame th {
            color: var(--text-dark) !important;
        }

        /* ==================== HIDE DEFAULTS ==================== */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .block-container {
            padding-top: 0 !important;
            max-width: 1100px;
        }

        /* ==================== MOBILE BASIC RESPONSIVENESS ==================== */
        @media (max-width: 768px) {
            .hero-section {
                padding: 1.5rem 1rem 1.5rem 1rem;
            }
            .hero-title {
                font-size: 1.8rem;
            }
            .hero-icons {
                gap: 0.5rem;
            }
            .hero-icon-box {
                min-width: 70px;
                padding: 0.5rem 0.6rem;
                font-size: 0.7rem;
            }
            .summary-grid {
                grid-template-columns: repeat(2, 1fr);
            }
            .inv-metrics {
                grid-template-columns: repeat(2, 1fr);
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ===================== 1. HERO SECTION =====================
    st.markdown(
        """
        <div class="hero-section">
            <div class="hero-content">
                <div class="hero-badge">EN²TECH 2026 &nbsp;|&nbsp; Akıllı ve Verimli Enerji Sistemleri</div>
                <h1 class="hero-title">ENERJİ <span>PUSULASI</span></h1>
                <p class="hero-subtitle">
                    OSB içindeki KOBİ ve orta ölçekli üretim tesisleri için veri temelli
                    enerji dönüşümü yatırım önceliklendirme ve hızlı ön fizibilite modeli
                </p>
                <p class="hero-subtitle-2">
                    Sanayide doğru enerji yatırımına yön veren veri temelli karar modeli
                </p>
                <div class="hero-icons">
                    <div class="hero-icon-box"><span class="icon">⚡</span>Enerji<br>Verimliliği</div>
                    <div class="hero-icon-box"><span class="icon">☀️</span>Çatı<br>GES</div>
                    <div class="hero-icon-box"><span class="icon">⏱️</span>Yük<br>Yönetimi</div>
                    <div class="hero-icon-box"><span class="icon">🔋</span>Batarya<br>Depolama</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="notice-banner">
            <span class="n-icon">⚠️</span>
            <span class="n-text">
                <strong>Önemli:</strong> Bu araç detaylı mühendislik fizibilitesinin yerine geçmez.
                Hızlı ön fizibilite ve yatırım önceliklendirme amacıyla çalışır.
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ===================== SESSION STATE =====================
    if "ornek_secim" not in st.session_state:
        st.session_state.ornek_secim = None

    def _ornek_sec(senaryo_no):
        st.session_state.ornek_secim = senaryo_no

    ov = ORNEK_VERILER.get(st.session_state.ornek_secim, {})

    def _idx(secenekler, key, varsayilan=0):
        if key in ov:
            try:
                return secenekler.index(ov[key])
            except ValueError:
                return varsayilan
        return varsayilan

    # ===================== 2. VERİ GİRİŞ BÖLÜMÜ =====================
    st.markdown(
        '<div class="section-header"><div class="dot"></div><h2>Veri Girişleri</h2></div>',
        unsafe_allow_html=True,
    )

    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.button("📋 Örnek 1: Dengeli KOBİ", on_click=_ornek_sec, args=("1",), type="primary", use_container_width=True)
    with col_s2:
        st.button("☀️ Örnek 2: GES Uygun Tesis", on_click=_ornek_sec, args=("2",), type="primary", use_container_width=True)
    with col_s3:
        st.button("⚡ Örnek 3: Verimlilik Öncelikli", on_click=_ornek_sec, args=("3",), type="primary", use_container_width=True)

    with st.expander("🏭  Temel Tesis Verileri", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            aylik_tuketim_kwh = st.number_input(
                "Aylık Tüketim (kWh/ay)", min_value=0,
                value=ov.get("aylik_tuketim_kwh", 100000), step=1000,
                help="Tesisinizin aylık toplam elektrik tüketimi",
            )
            aylik_fatura_tl = st.number_input(
                "Aylık Fatura (TL/ay)", min_value=0,
                value=ov.get("aylik_fatura_tl", 500000), step=10000,
                help="Aylık elektrik faturası tutarı",
            )
            maksimum_talep_kw = st.number_input(
                "Maksimum Talep (kW)", min_value=0,
                value=ov.get("maksimum_talep_kw", 500), step=10,
                help="Tesisinizin en yüksek anlık güç talebi",
            )
        with col2:
            gunluk_calisma_saati = st.slider(
                "Günlük Çalışma Saati", min_value=0, max_value=24,
                value=ov.get("gunluk_calisma_saati", 8),
            )
            haftalik_calisma_gunu = st.slider(
                "Haftalık Çalışma Günü", min_value=1, max_value=7,
                value=ov.get("haftalik_calisma_gunu", 5),
            )
            gunduz_calisma_orani = st.slider(
                "Gündüz Çalışma Oranı (%)", min_value=0, max_value=100,
                value=ov.get("gunduz_calisma_orani", 50),
                help="Üretim faaliyetinin gündüz saatlerinde gerçekleşme oranı",
            )
        with col3:
            faaliyet_turu_secenekler = ["ton", "adet", "m2", "metre", "calisma_saati", "diger"]
            faaliyet_gostergesi_turu = st.selectbox(
                "Faaliyet Göstergesi Türü", faaliyet_turu_secenekler,
                index=_idx(faaliyet_turu_secenekler, "faaliyet_gostergesi_turu"),
            )
            aylik_faaliyet_miktari = st.number_input(
                "Aylık Faaliyet Miktarı", min_value=0,
                value=ov.get("aylik_faaliyet_miktari", 10000), step=100,
            )
            yatirim_butcesi_tl = st.number_input(
                "Yatırım Bütçesi (TL)", min_value=0,
                value=ov.get("yatirim_butcesi_tl", 5000000), step=100000,
                help="Bu dönüşüm için ayrılabilecek toplam bütçe",
            )
            tolerans_secenekler = ["dusuk", "orta", "yuksek"]
            tolerans_etiketler = {"dusuk": "Düşük", "orta": "Orta", "yuksek": "Yüksek"}
            uretim_kesintisi_toleransi = st.selectbox(
                "Üretim Kesintisi Toleransı", tolerans_secenekler,
                index=_idx(tolerans_secenekler, "uretim_kesintisi_toleransi"),
                format_func=lambda x: tolerans_etiketler[x],
            )

    yogunluk_secenekler = ["yok", "dusuk", "orta", "yuksek"]
    yogunluk_etiketler = {"yok": "Yok", "dusuk": "Düşük", "orta": "Orta", "yuksek": "Yüksek"}

    with st.expander("⚡  Enerji Verimliliği Girdileri"):
        col1, col2 = st.columns(2)
        with col1:
            basincli_hava_yogunlugu = st.selectbox(
                "Basınçlı Hava Yoğunluğu", yogunluk_secenekler,
                index=_idx(yogunluk_secenekler, "basincli_hava_yogunlugu"),
                format_func=lambda x: yogunluk_etiketler[x],
            )
            aydinlatma_yas_secenekler = ["yeni", "orta", "eski"]
            aydinlatma_yas_etiketler = {"yeni": "Yeni", "orta": "Orta", "eski": "Eski"}
            aydinlatma_sistem_yasi = st.selectbox(
                "Aydınlatma Sistem Yaşı", aydinlatma_yas_secenekler,
                index=_idx(aydinlatma_yas_secenekler, "aydinlatma_sistem_yasi"),
                format_func=lambda x: aydinlatma_yas_etiketler[x],
            )
            motor_surucu_onemi = st.selectbox(
                "Motor Sürücü Önemi", yogunluk_secenekler,
                index=_idx(yogunluk_secenekler, "motor_surucu_onemi"),
                format_func=lambda x: yogunluk_etiketler[x], key="motor",
            )
        with col2:
            hvac_onemi = st.selectbox(
                "HVAC Önemi", ["dusuk", "orta", "yuksek"],
                index=_idx(["dusuk", "orta", "yuksek"], "hvac_onemi"),
                format_func=lambda x: yogunluk_etiketler[x],
            )
            yardimci_servis_belirginligi = st.selectbox(
                "Yardımcı Servis Belirginliği", ["dusuk", "orta", "yuksek"],
                index=_idx(["dusuk", "orta", "yuksek"], "yardimci_servis_belirginligi"),
                format_func=lambda x: yogunluk_etiketler[x],
            )

    with st.expander("☀️  Çatı GES Girdileri"):
        col1, col2 = st.columns(2)
        with col1:
            kullanilabilir_cati_alani_m2 = st.number_input(
                "Kullanılabilir Çatı Alanı (m²)", min_value=0,
                value=ov.get("kullanilabilir_cati_alani_m2", 1000), step=50,
            )
        with col2:
            cati_uyg_secenekler = ["uygun_degil", "kismen_uygun", "uygun"]
            cati_uyg_etiketler = {"uygun_degil": "Uygun Değil", "kismen_uygun": "Kısmen Uygun", "uygun": "Uygun"}
            cati_uygunlugu = st.selectbox(
                "Çatı Uygunluğu", cati_uyg_secenekler,
                index=_idx(cati_uyg_secenekler, "cati_uygunlugu"),
                format_func=lambda x: cati_uyg_etiketler[x],
            )

    onem_secenekler = ["dusuk", "orta", "yuksek"]
    with st.expander("⏱️  Yük Yönetimi Girdileri"):
        col1, col2 = st.columns(2)
        with col1:
            yuk_kaydirma_esnekligi = st.selectbox(
                "Yük Kaydırma Esnekliği", onem_secenekler,
                index=_idx(onem_secenekler, "yuk_kaydirma_esnekligi"),
                format_func=lambda x: yogunluk_etiketler[x], key="yuk_esn",
            )
        with col2:
            pik_saatlerde_uretim_zorunlulugu = st.selectbox(
                "Pik Saatlerde Üretim Zorunluluğu", onem_secenekler,
                index=_idx(onem_secenekler, "pik_saatlerde_uretim_zorunlulugu"),
                format_func=lambda x: yogunluk_etiketler[x], key="pik",
            )

    with st.expander("🔋  Batarya Depolama Girdileri"):
        col1, col2 = st.columns(2)
        with col1:
            kritik_yuk_hassasiyeti = st.selectbox(
                "Kritik Yük Hassasiyeti", onem_secenekler,
                index=_idx(onem_secenekler, "kritik_yuk_hassasiyeti"),
                format_func=lambda x: yogunluk_etiketler[x], key="kritik",
            )
        with col2:
            ikili_secenekler = ["hayir", "evet"]
            ikili_etiketler = {"hayir": "Hayır", "evet": "Evet"}
            mevcut_veya_planlanan_ges = st.selectbox(
                "Mevcut veya Planlanan GES", ikili_secenekler,
                index=_idx(ikili_secenekler, "mevcut_veya_planlanan_ges"),
                format_func=lambda x: ikili_etiketler[x],
            )

    # --- Girdi özet paneli ---
    st.markdown(
        f"""
        <div class="summary-panel">
            <h3>📊 Girdi Özeti</h3>
            <div class="summary-grid">
                <div class="summary-item"><div class="val">{aylik_tuketim_kwh:,.0f}</div><div class="lbl">kWh / ay</div></div>
                <div class="summary-item"><div class="val">₺{aylik_fatura_tl:,.0f}</div><div class="lbl">TL / ay</div></div>
                <div class="summary-item"><div class="val">{maksimum_talep_kw:,.0f}</div><div class="lbl">kW maks talep</div></div>
                <div class="summary-item"><div class="val">%{gunduz_calisma_orani}</div><div class="lbl">gündüz oranı</div></div>
                <div class="summary-item"><div class="val">₺{yatirim_butcesi_tl:,.0f}</div><div class="lbl">yatırım bütçesi</div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ===================== HESAPLAMA =====================
    hesapla_btn = st.button("🚀 Analizi Çalıştır", type="primary", use_container_width=True)

    if hesapla_btn:
        if aylik_tuketim_kwh <= 0:
            st.error("Aylık tüketim sıfırdan büyük olmalıdır.")
            return
        if aylik_fatura_tl <= 0:
            st.error("Aylık fatura sıfırdan büyük olmalıdır.")
            return

        veri = {
            "aylik_tuketim_kwh": aylik_tuketim_kwh,
            "aylik_fatura_tl": aylik_fatura_tl,
            "maksimum_talep_kw": maksimum_talep_kw,
            "gunluk_calisma_saati": gunluk_calisma_saati,
            "haftalik_calisma_gunu": haftalik_calisma_gunu,
            "gunduz_calisma_orani": gunduz_calisma_orani,
            "faaliyet_gostergesi_turu": faaliyet_gostergesi_turu,
            "aylik_faaliyet_miktari": aylik_faaliyet_miktari,
            "yatirim_butcesi_tl": yatirim_butcesi_tl,
            "uretim_kesintisi_toleransi": uretim_kesintisi_toleransi,
            "basincli_hava_yogunlugu": basincli_hava_yogunlugu,
            "aydinlatma_sistem_yasi": aydinlatma_sistem_yasi,
            "motor_surucu_onemi": motor_surucu_onemi,
            "hvac_onemi": hvac_onemi,
            "yardimci_servis_belirginligi": yardimci_servis_belirginligi,
            "kullanilabilir_cati_alani_m2": kullanilabilir_cati_alani_m2,
            "cati_uygunlugu": cati_uygunlugu,
            "yuk_kaydirma_esnekligi": yuk_kaydirma_esnekligi,
            "pik_saatlerde_uretim_zorunlulugu": pik_saatlerde_uretim_zorunlulugu,
            "kritik_yuk_hassasiyeti": kritik_yuk_hassasiyeti,
            "mevcut_veya_planlanan_ges": mevcut_veya_planlanan_ges,
        }

        sonuc = hesapla(veri)

        # ===================== 3. SONUÇ DASHBOARD =====================

        # A. Sonuç başlık bandı
        st.markdown(
            """
            <div class="results-banner">
                <h2>🏆 Önceliklendirme Sonuçları</h2>
                <p>Yatırım seçenekleri teknik, ekonomik ve çevresel ölçütlere göre sıralandı</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        siralama = sonuc["siralama"]

        # B. 4 yatırım kartı (2×2 düzen)
        col_left, col_right = st.columns(2)
        for i, (kod, skor) in enumerate(siralama):
            oncelik_no = sonuc["oncelik"][kod]
            ad = YATIRIM_ETIKETLERI[kod]
            ikon = YATIRIM_IKONLARI[kod]
            rank_cls = f"r{oncelik_no}"
            card_cls = "inv-card rank-1-card" if oncelik_no == 1 else "inv-card"
            score_cls = "inv-score top" if oncelik_no == 1 else "inv-score"

            card_html = f"""
            <div class="{card_cls}">
                <div class="inv-card-header">
                    <div class="inv-rank {rank_cls}">{oncelik_no}</div>
                    <span class="inv-icon">{ikon}</span>
                    <span class="inv-name">{ad}</span>
                    <span class="{score_cls}">{skor:.1f}</span>
                </div>
                <div class="inv-metrics">
                    <div class="inv-metric"><div class="m-label">Ekonomik Çekicilik</div><div class="m-value">{sonuc['E'][kod]:.1f}</div></div>
                    <div class="inv-metric"><div class="m-label">Teknik Uygunluk</div><div class="m-value">{sonuc['T'][kod]:.1f}</div></div>
                    <div class="inv-metric"><div class="m-label">Performans Pot.</div><div class="m-value">{sonuc['P'][kod]:.1f}</div></div>
                    <div class="inv-metric"><div class="m-label">Uygulanabilirlik</div><div class="m-value">{sonuc['U'][kod]:.1f}</div></div>
                    <div class="inv-metric"><div class="m-label">Çevresel Etki</div><div class="m-value">{sonuc['C'][kod]:.1f}</div></div>
                    <div class="inv-metric"><div class="m-label">Yatırım</div><div class="m-value">{format_tl(sonuc['yatirim'][kod])}</div></div>
                    <div class="inv-metric"><div class="m-label">Yıllık Tasarruf</div><div class="m-value">{format_tl(sonuc['yillik_tasarruflar'][kod])}</div></div>
                    <div class="inv-metric"><div class="m-label">Geri Ödeme</div><div class="m-value">{format_yil(sonuc['geri_odeme'][kod])}</div></div>
                </div>
            </div>
            """
            target = col_left if i % 2 == 0 else col_right
            target.markdown(card_html, unsafe_allow_html=True)

        # C. Grafikler
        st.markdown(
            '<div class="section-header"><div class="dot"></div><h2>Teknik ve Ekonomik Değerlendirme</h2></div>',
            unsafe_allow_html=True,
        )

        # Bar chart
        bar_labels = [YATIRIM_ETIKETLERI[k] for k, _ in siralama]
        bar_values = [round(v, 1) for _, v in siralama]
        bar_colors = ["#37B5E5", "#2E73D8", "#5A7BA6", "#8899AA"]

        fig_bar = go.Figure(
            go.Bar(
                x=bar_values, y=bar_labels, orientation="h",
                marker_color=bar_colors[:len(bar_labels)],
                text=[f"{v:.1f}" for v in bar_values],
                textposition="outside",
                textfont=dict(size=14, color="#0E2E5C", family="Inter"),
            )
        )
        fig_bar.update_layout(
            xaxis_title="Toplam Skor", yaxis=dict(autorange="reversed"),
            height=260, margin=dict(l=10, r=30, t=10, b=40),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter", size=13, color="#0E2E5C"),
            xaxis=dict(range=[0, 105], gridcolor="#D4E0F0"),
        )

        st.markdown('<div class="chart-card"><div class="chart-card-title">📊 Nihai Yatırım Öncelik Sıralaması</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_bar, use_container_width=True, key="bar_chart")
        st.markdown('</div>', unsafe_allow_html=True)

        # Grouped bar + Radar yan yana
        kriter_labels = ["Ekonomik\nÇekicilik", "Teknik\nUygunluk", "Performans\nPotansiyeli", "Uygulanabilirlik", "Çevresel\nEtki"]
        kriter_keys = ["E", "T", "P", "U", "C"]
        renk_paleti = {"EV": "#1F5FBF", "GES": "#37B5E5", "YK": "#00C16A", "BAT": "#5A7BA6"}

        col_g, col_r = st.columns(2)

        with col_g:
            fig_grouped = go.Figure()
            for kod in ["EV", "GES", "YK", "BAT"]:
                values = [round(sonuc[k][kod], 1) for k in kriter_keys]
                fig_grouped.add_trace(go.Bar(
                    name=YATIRIM_ETIKETLERI[kod], x=kriter_labels, y=values,
                    marker_color=renk_paleti[kod],
                    text=[f"{v:.0f}" for v in values],
                    textposition="outside",
                    textfont=dict(size=10, color="#0E2E5C"),
                ))
            fig_grouped.update_layout(
                barmode="group", yaxis_title="Skor", height=420,
                margin=dict(l=10, r=10, t=30, b=40),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=11, color="#0E2E5C")),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter", size=12, color="#0E2E5C"),
                yaxis=dict(range=[0, 105], gridcolor="#D4E0F0"),
            )
            st.markdown('<div class="chart-card"><div class="chart-card-title">📈 Kriter Bazlı Karşılaştırma</div>', unsafe_allow_html=True)
            st.plotly_chart(fig_grouped, use_container_width=True, key="grouped_chart")
            st.markdown('</div>', unsafe_allow_html=True)

        with col_r:
            radar_labels = ["Ekonomik Çekicilik", "Teknik Uygunluk", "Performans Potansiyeli", "Uygulanabilirlik", "Çevresel Etki"]
            fig_radar = go.Figure()
            for kod in ["EV", "GES", "YK", "BAT"]:
                values = [round(sonuc[k][kod], 1) for k in kriter_keys]
                values_closed = values + [values[0]]
                labels_closed = radar_labels + [radar_labels[0]]
                fig_radar.add_trace(go.Scatterpolar(
                    r=values_closed, theta=labels_closed, fill="toself",
                    name=YATIRIM_ETIKETLERI[kod], line_color=renk_paleti[kod], opacity=0.7,
                ))
            fig_radar.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 100], gridcolor="#D4E0F0", tickfont=dict(color="#0E2E5C")),
                    angularaxis=dict(tickfont=dict(color="#0E2E5C", size=11)),
                    bgcolor="rgba(0,0,0,0)",
                ),
                height=420, margin=dict(l=50, r=50, t=30, b=30),
                legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5, font=dict(size=11, color="#0E2E5C")),
                paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter", size=12, color="#0E2E5C"),
            )
            st.markdown('<div class="chart-card"><div class="chart-card-title">🎯 Radar Görünümü</div>', unsafe_allow_html=True)
            st.plotly_chart(fig_radar, use_container_width=True, key="radar_chart")
            st.markdown('</div>', unsafe_allow_html=True)

        # Özet tablo
        st.markdown('<div class="section-header"><div class="dot"></div><h2>Özet Tablo</h2></div>', unsafe_allow_html=True)

        tablo_data = []
        for kod, _ in siralama:
            tablo_data.append({
                "Öncelik": sonuc["oncelik"][kod],
                "Yatırım Türü": YATIRIM_ETIKETLERI[kod],
                "Toplam Skor": round(sonuc["toplam"][kod], 1),
                "Ekonomik": round(sonuc["E"][kod], 1),
                "Teknik": round(sonuc["T"][kod], 1),
                "Performans": round(sonuc["P"][kod], 1),
                "Uygulanabilirlik": round(sonuc["U"][kod], 1),
                "Çevresel": round(sonuc["C"][kod], 1),
                "Yatırım (TL)": format_tl(sonuc["yatirim"][kod]),
                "Yıllık Tasarruf (TL)": format_tl(sonuc["yillik_tasarruflar"][kod]),
                "Geri Ödeme (yıl)": format_yil(sonuc["geri_odeme"][kod]),
            })

        df = pd.DataFrame(tablo_data)
        st.dataframe(
            df, use_container_width=True, hide_index=True,
            column_config={
                "Öncelik": st.column_config.NumberColumn("Öncelik", width="small"),
                "Toplam Skor": st.column_config.NumberColumn("Toplam Skor", format="%.1f"),
            },
        )

        # Excel indirme butonu
        st.markdown("")
        excel_data = excel_olustur(veri, sonuc)
        st.download_button(
            label="📥 Excel Çıktısını İndir",
            data=excel_data,
            file_name="enerji_pusulasi_sonuc.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

        # ===================== ÖN FİZİBİLİTE ÖZETİ =====================
        st.markdown(
            '<div class="section-header"><div class="dot"></div><h2>Ön Fizibilite Özeti</h2></div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="notice-banner">
                <span class="n-icon">📋</span>
                <span class="n-text">
                    Bu çıktı detaylı mühendislik fizibilitesinin yerine geçmez;
                    hızlı ön fizibilite ve yatırım önceliklendirme amacıyla üretilmiştir.
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Ön fizibilite tablosu
        fizibilite_data = []
        for kod, _ in siralama:
            toplam_s = sonuc["toplam"][kod]
            go_val = sonuc["geri_odeme"][kod]
            etiket = durum_etiketi(toplam_s, go_val)
            fizibilite_data.append({
                "Yatırım Türü": YATIRIM_ETIKETLERI[kod],
                "Toplam Skor": round(toplam_s, 1),
                "Öncelik": sonuc["oncelik"][kod],
                "Tahmini Yatırım (TL)": format_tl(sonuc["yatirim"][kod]),
                "Tahmini Yıllık Tasarruf (TL)": format_tl(sonuc["yillik_tasarruflar"][kod]),
                "Geri Ödeme (yıl)": format_yil(go_val),
                "Teknik Uygunluk": round(sonuc["T"][kod], 1),
                "Uygulanabilirlik": round(sonuc["U"][kod], 1),
                "Durum": etiket,
            })

        df_fizibilite = pd.DataFrame(fizibilite_data)
        st.dataframe(
            df_fizibilite, use_container_width=True, hide_index=True,
            column_config={
                "Öncelik": st.column_config.NumberColumn("Öncelik", width="small"),
                "Toplam Skor": st.column_config.NumberColumn("Toplam Skor", format="%.1f"),
                "Teknik Uygunluk": st.column_config.NumberColumn("Teknik Uygunluk", format="%.1f"),
                "Uygulanabilirlik": st.column_config.NumberColumn("Uygulanabilirlik", format="%.1f"),
            },
        )

        # Ön fizibilite kartları
        for kod, _ in siralama:
            toplam_s = sonuc["toplam"][kod]
            go_val = sonuc["geri_odeme"][kod]
            etiket = durum_etiketi(toplam_s, go_val)
            ikon = YATIRIM_IKONLARI[kod]
            ad = YATIRIM_ETIKETLERI[kod]

            if etiket == "Güçlü öncelik":
                etiket_renk = "#00C16A"
                etiket_bg = "rgba(0,193,106,0.1)"
            elif etiket == "Değerlendirilmeli":
                etiket_renk = "#E8A830"
                etiket_bg = "rgba(232,168,48,0.1)"
            else:
                etiket_renk = "#8899AA"
                etiket_bg = "rgba(136,153,170,0.1)"

            st.markdown(
                f"""
                <div style="background: #FFFFFF; border: 1px solid #D4E0F0; border-radius: 14px;
                            padding: 1.2rem 1.5rem; margin-bottom: 0.7rem;
                            box-shadow: 0 2px 10px rgba(14,46,92,0.06);">
                    <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem;">
                        <div style="display: flex; align-items: center; gap: 0.6rem;">
                            <span style="font-size: 1.4rem;">{ikon}</span>
                            <span style="font-size: 1.05rem; font-weight: 700; color: #0E2E5C;">{ad}</span>
                            <span style="font-size: 0.85rem; font-weight: 700; color: #1F5FBF;">({toplam_s:.1f} puan – #{sonuc['oncelik'][kod]})</span>
                        </div>
                        <span style="display: inline-block; background: {etiket_bg}; color: {etiket_renk};
                                      border: 1px solid {etiket_renk}; border-radius: 20px;
                                      padding: 0.25rem 0.9rem; font-size: 0.8rem; font-weight: 700;">
                            {etiket}
                        </span>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                                gap: 0.5rem; margin-top: 0.8rem;">
                        <div style="text-align: center; background: #EEF3FA; border-radius: 8px; padding: 0.5rem;">
                            <div style="font-size: 0.7rem; color: #4A6B8A; font-weight: 600;">Yatırım Maliyeti</div>
                            <div style="font-size: 0.95rem; font-weight: 700; color: #0E2E5C;">{format_tl(sonuc['yatirim'][kod])}</div>
                        </div>
                        <div style="text-align: center; background: #EEF3FA; border-radius: 8px; padding: 0.5rem;">
                            <div style="font-size: 0.7rem; color: #4A6B8A; font-weight: 600;">Yıllık Tasarruf</div>
                            <div style="font-size: 0.95rem; font-weight: 700; color: #0E2E5C;">{format_tl(sonuc['yillik_tasarruflar'][kod])}</div>
                        </div>
                        <div style="text-align: center; background: #EEF3FA; border-radius: 8px; padding: 0.5rem;">
                            <div style="font-size: 0.7rem; color: #4A6B8A; font-weight: 600;">Geri Ödeme</div>
                            <div style="font-size: 0.95rem; font-weight: 700; color: #0E2E5C;">{format_yil(go_val)}</div>
                        </div>
                        <div style="text-align: center; background: #EEF3FA; border-radius: 8px; padding: 0.5rem;">
                            <div style="font-size: 0.7rem; color: #4A6B8A; font-weight: 600;">Teknik Uygunluk</div>
                            <div style="font-size: 0.95rem; font-weight: 700; color: #0E2E5C;">{sonuc['T'][kod]:.1f}</div>
                        </div>
                        <div style="text-align: center; background: #EEF3FA; border-radius: 8px; padding: 0.5rem;">
                            <div style="font-size: 0.7rem; color: #4A6B8A; font-weight: 600;">Uygulanabilirlik</div>
                            <div style="font-size: 0.95rem; font-weight: 700; color: #0E2E5C;">{sonuc['U'][kod]:.1f}</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # JSON
        with st.expander("🔍 Detaylı Sonuç Verisi (JSON)"):
            json_cikti = {}
            for kod, _ in siralama:
                json_cikti[YATIRIM_ETIKETLERI[kod]] = {
                    "oncelik_sirasi": sonuc["oncelik"][kod],
                    "toplam_skor": round(sonuc["toplam"][kod], 2),
                    "ekonomik_cekicilik_skoru": round(sonuc["E"][kod], 2),
                    "teknik_uygunluk_skoru": round(sonuc["T"][kod], 2),
                    "performans_potansiyeli_skoru": round(sonuc["P"][kod], 2),
                    "uygulanabilirlik_skoru": round(sonuc["U"][kod], 2),
                    "cevresel_etki_skoru": round(sonuc["C"][kod], 2),
                    "yatirim_maliyeti_tl": round(sonuc["yatirim"][kod], 0),
                    "yillik_tasarruf_tl": round(sonuc["yillik_tasarruflar"][kod], 0),
                    "basit_geri_odeme_yili": round(sonuc["geri_odeme"][kod], 2),
                }
            st.json(json_cikti)

        # D. Açıklama alanı
        aciklama = aciklama_uret(veri, sonuc)
        st.markdown(
            f"""
            <div class="explanation-card">
                <div class="exp-title">💡 Değerlendirme Özeti</div>
                {aciklama}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Ara hesaplama detayları
        with st.expander("⚙️ Ara Hesaplama Detayları"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Genel Göstergeler**")
                st.write(f"- Birim enerji maliyeti: {sonuc['birim_enerji_maliyeti']:.2f} TL/kWh")
                st.write(f"- Yıllık tüketim: {sonuc['yillik_tuketim']:,.0f} kWh")
                st.write(f"- Yıllık fatura: {format_tl(sonuc['yillik_fatura'])}")
                st.write(f"- EV fırsat skoru: {sonuc['ev_firsat']:.1f}")
                st.write(f"- Öz tüketim hedefi: {sonuc['oz_tuketim_hedefi']:.2f}")
            with col2:
                st.markdown("**GES & Batarya**")
                st.write(f"- PV ihtiyaç: {sonuc['pv_ihtiyac']:.1f} kWp")
                st.write(f"- PV çatı maks: {sonuc['pv_cati_max']:.1f} kWp")
                st.write(f"- PV kurulu güç: {sonuc['pv_kwp']:.1f} kWp")
                st.write(f"- GES yıllık üretim: {sonuc['yillik_uretim_ges']:,.0f} kWh")
                st.write(f"- GES faydalı enerji: {sonuc['faydali_enerji_ges']:,.0f} kWh")
                st.write(f"- Kritik güç: {sonuc['kritik_guc_kw']:.1f} kW")
                st.write(f"- Batarya süresi: {sonuc['batarya_sure']} saat")
                st.write(f"- Batarya kapasitesi: {sonuc['batarya_kapasitesi_kwh']:.1f} kWh")

            st.markdown("**Tasarruf Oranları**")
            st.write(f"- EV: %{sonuc['tasarruf_orani_ev'] * 100:.1f}")
            st.write(f"- YK: %{sonuc['tasarruf_orani_yk'] * 100:.1f}")
            st.write(f"- BAT: %{sonuc['tasarruf_orani_bat'] * 100:.1f}")

    # ===================== FOOTER =====================
    st.markdown(
        """
        <div class="ep-footer">
            <strong>EN²TECH 2026</strong> – Enerji Pusulası &nbsp;|&nbsp;
            Hızlı Ön Fizibilite & Yatırım Önceliklendirme<br>
            <em>Bu araç detaylı mühendislik fizibilitesinin yerine geçmez.</em>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
