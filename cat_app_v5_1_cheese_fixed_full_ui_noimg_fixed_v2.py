# cat_app_v5_1_cheese_fixed_full_ui_noimg.py
# -*- coding: utf-8 -*-
import math
import hashlib
import base64
import pandas as pd
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="집사 밥상", page_icon="🐾", layout="wide")

# ----------------- Cute & Clean Global Styles -----------------
st.markdown("""
<style>
html, body {background: #FFF9F2;}
.block-container {padding-top: 2.5rem; padding-bottom: 2rem;}

/* HERO */
.brand-hero {text-align:center; margin-bottom: .5rem; padding-top: .75rem; overflow: visible;}
.logo-wrap {
  display:inline-flex; align-items:center; justify-content:center;
  width:112px; height:112px; border-radius:28px;
  background: radial-gradient(120px 120px at 50% 40%, #FFE6D3 0%, #FFF9F2 70%);
  border: 1px solid #F5D9C8;
  filter: drop-shadow(0 10px 22px rgba(248, 184, 139, .35));
}
.brand-logo {width:84px; height:84px; border-radius:20px; object-fit:contain; background:#fff;}
.brand-title {font-weight:900; letter-spacing:.02em; font-size: 2.1rem; color:#3d3d3d; margin: .6rem 0 0 0;}
.brand-sub {color:#7a6b5f; font-size:.96rem; margin-top:.2rem;}

/* Form 카드 느낌 */
.section-card {background:#FFFFFF;border:1px solid #F0E2D8;border-radius:18px;padding: 1rem 1rem 0.5rem 1rem; 
  box-shadow: 0 4px 14px rgba(0,0,0,.04); margin-top: 1rem;}
.section-card h3 {margin:.25rem 0 1rem 0; font-size:1.15rem;}

/* Pills & tags */
.small {font-size: .9rem; color:#666;}
.muted {color:#8a8a8a;}
.pill {
  display:inline-block; padding:.18rem .6rem; border-radius:9999px;
  background:#FFF8E1;               /* 🟡 밝고 맑은 노란 계열 */
  margin-right:.25rem; font-size:.75rem; color:#5f3b23;
  border:1px solid #FFE9A6;         /* 부드러운 노랑 테두리 */
}
.tag {background:#EEF2FF;color:#4F46E5;border-color:#E3E7FE;}
.reason {background:#ECFDF5;color:#065F46;border-color:#CCF5E7;}

/* Cards */
.card {
  background:#FFFFFF; border:1px solid #F0E2D8; border-radius:18px;
  padding: 1rem; box-shadow: 0 4px 14px rgba(0,0,0,.04);
  height: 100%;
  display:flex; flex-direction:column; justify-content:space-between;
}
.card h3 {margin:.25rem 0 .4rem 0; font-size:1.05rem;}
.card .meta {font-size:.9rem; color:#6b6b6b; margin-bottom:.35rem;}
.card .score {margin:.2rem 0 .3rem 0;}
.card .actions {margin-top:.5rem}

/* 버튼 시각 통일 & 정렬 개선 */
.stButton > button {border-radius:9999px; border:1px solid #f2d6c5; background:#fff; padding:.5rem 1rem; width:100%;}
.stButton > button:hover {background:#FFF0E6; border-color:#f0c5ad;}

/* 두 번째 페이지(결과) 컬럼 간격 소폭 축소로 밀도 ↑ */
[data-testid="column"] {padding: 0 .5rem !important;}
</style>
""", unsafe_allow_html=True)

# ----------------- Data Loader -----------------
@st.cache_data
def load_catalog(path):
    df = pd.read_csv(path)
    text_cols = ["brand","name","type","texture","protein","ingredients","price_tier","tags","category","country","product_url","image_url","availability_region","sku"]
    for c in text_cols:
        if c in df.columns:
            df[c] = df[c].astype(str).fillna("")
    num_cols = ["moisture_pct","kcal_per_100g","magnesium_mg_per_100kcal","phosphorus_pct_dm","sodium_pct_dm",
                "crude_protein_pct_dm","crude_fat_pct_dm","crude_fiber_pct_dm","ash_pct_dm","omega3_pct_dm","calcium_pct_dm",
                "package_size_g","price_krw","palatability_score","rating_count","treat_kcal_per_piece"]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in ["grain_free","single_protein","veterinary_diet","indoor_suitable","neutered_suitable"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.lower().isin(["true","1","y","yes"])
    return df

DEFAULT_PATHS = ["catalog.csv", "real_brands_catalog_max.csv"]
data = None
for p in DEFAULT_PATHS:
    try:
        data = load_catalog(p)
        break
    except Exception:
        pass

if data is None:
    st.error("카탈로그 CSV를 찾지 못했어요. 폴더에 catalog.csv를 넣거나 파일 업로드를 사용하세요.")
    uploaded = st.file_uploader("카탈로그 CSV 업로드", type=["csv"])
    if uploaded:
        data = load_catalog(uploaded)
    else:
        st.stop()

# ----------------- Helpers -----------------
ALLERGY_SYNONYMS = {
    "닭": ["닭","치킨","계육","chicken"],
    "소": ["소","소고기","비프","beef"],
    "어류": ["어류","생선","연어","참치","고등어","fish","salmon","tuna","mackerel"],
    "오리": ["오리","duck"],
    "양": ["양","램","양고기","lamb"],
    "칠면조": ["칠면조","터키","turkey"],
    "계란": ["계란","달걀","egg"],
    "유제품": ["우유","유청","치즈","lactose","milk","whey"],
    "곡물": ["밀","보리","옥수수","글루텐","wheat","corn","gluten"]
}

def expand_allergy_terms(tokens):
    expanded = set()
    for t in tokens:
        t = t.strip().lower()
        if not t:
            continue
        expanded.add(t)
        for syns in ALLERGY_SYNONYMS.values():
            low = [s.lower() for s in syns]
            if t in low:
                expanded.update(low)
    return expanded

def life_stage(age):
    try:
        a = float(age)
    except Exception:
        a = 3.0
    return "키튼" if a < 1 else ("어덜트" if a < 10 else "시니어")

def estimate_daily_kcal(weight, activity, neutered, stage):
    try:
        w = max(0.5, float(weight))
    except Exception:
        w = 4.0
    rer = 70 * (w ** 0.75)
    factor = 1.0
    if neutered == "예":
        factor -= 0.05
    if activity == "낮음":
        factor -= 0.1
    elif activity == "높음":
        factor += 0.15
    if stage == "키튼":
        factor += 0.25
    elif stage == "시니어":
        factor -= 0.05
    return max(120, int(round(rer * factor)))

# ----------------- State -----------------
if "step" not in st.session_state:
    st.session_state.update(step=1, form={}, favorites=set(), dislikes=set())

def item_id(row):
    base = str(row.get("sku") or row.get("name") or f"{row.get('brand')}_{row.get('product_url')}")
    h = hashlib.md5(base.encode("utf-8")).hexdigest()[:8]
    return f"{base}-{h}"

# --- Logo util: embed local file as data URI ---
def _logo_data_uri():
    candidates = []
    try:
        candidates.append(Path(__file__).parent / "cheese_cat_logo.png")
    except NameError:
        pass
    candidates.append(Path("cheese_cat_logo.png"))
    for p in candidates:
        if p.exists():
            mime = "image/png" if p.suffix.lower() in [".png",".apng"] else "image/jpeg"
            b64 = base64.b64encode(p.read_bytes()).decode("ascii")
            return f"data:{mime};base64,{b64}"
    return None

# ----------------- STEP 1: Hero + Form -----------------
if st.session_state.step == 1:
    logo_src = _logo_data_uri() or "https://picsum.photos/seed/cat/96/96"
    brand_name = "집사 밥상"

    st.markdown(f"""
    <div class="brand-hero">
        <div class="logo-wrap">
            <img class="brand-logo" src="{logo_src}" alt="logo"/>
        </div>
        <div class="brand-title">{brand_name}</div>
        <div class="brand-sub">오늘도 우리 고양이를 위한 한 끼 💕</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("### 1) 반려묘 정보")
    with st.form("info_form", clear_on_submit=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            weight = st.number_input("몸무게(kg)", 0.5, 20.0, 4.0, 0.1, key="f_weight")
            age = st.number_input("나이(년)", 0.0, 25.0, 3.0, 0.5, key="f_age")
        with c2:
            neutered = st.selectbox("중성화", ["예","아니오"], index=0, key="f_neutered")
            activity = st.selectbox("활동량", ["낮음","보통","높음"], index=1, key="f_activity")
        with c3:
            conditions = st.multiselect("건강/목적",
                ["비만 경향","FLUTD/요로기계","신장 질환(CKD)","간 질환","소화 민감성/IBD","헤어볼","치아 문제"],
                key="f_conditions")

        st.markdown("### 2) 알러지")
        c4, c5 = st.columns(2)
        with c4:
            base_allergy = st.multiselect("자주 있는 알러지", list(ALLERGY_SYNONYMS.keys()), key="f_base_allergy")
        with c5:
            custom_allergy = st.text_input("기타 알러지(쉼표 , 로 구분)", key="f_custom_allergy")

        st.markdown("### 3) 기본 필터")
        brands = ["전체"] + sorted([b for b in data["brand"].dropna().unique() if b])
        sel_brands = st.multiselect("브랜드", brands, default=["전체"], key="f_sel_brands")
        price_opts = ["전체","저가","중간","프리미엄"]
        sel_prices = st.multiselect("가격대", price_opts, default=["전체"], key="f_sel_prices")
        textures = ["전체","드라이","습식/파우치"]
        sel_textures = st.multiselect("형태", textures, default=["전체"], key="f_sel_textures")
        proteins = ["전체","닭","어류","소","오리","양","칠면조"]
        sel_proteins = st.multiselect("단백질", proteins, default=["전체"], key="f_sel_proteins")

        submitted = st.form_submit_button("다음 단계 → 추천 보기", use_container_width=True)
        if submitted:
            st.session_state.form = dict(
                weight=weight, age=age, neutered=neutered, activity=activity, conditions=conditions,
                base_allergy=base_allergy, custom_allergy=custom_allergy, sel_brands=sel_brands,
                sel_prices=sel_prices, sel_textures=sel_textures, sel_proteins=sel_proteins
            )
            st.session_state.step = 2
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ----------------- STEP 2: Results -----------------
if st.session_state.step == 2:
    f = st.session_state.form
    stage = life_stage(f.get("age", 3.0))
    daily_kcal = estimate_daily_kcal(f.get("weight", 4.0), f.get("activity", "보통"), f.get("neutered", "예"), stage)
    st.success(f"권장 1일 필요 열량: **약 {daily_kcal} kcal/일** (간식은 보통 {int(daily_kcal*0.1)} kcal 이하) · 생애주기: **{stage}**")

    custom_tokens = [t.strip() for t in f.get("custom_allergy","").split(",") if t.strip()]
    allergies = set([a.lower() for a in f.get("base_allergy",[])]) | set([t.lower() for t in custom_tokens])
    expanded = expand_allergy_terms(allergies)

    with st.sidebar:
        st.header("🔎 추가 필터")
        price_series = data.get("price_krw", pd.Series([0])).fillna(0)
        try:
            min_price = int(price_series.min())
            max_price = int(max(price_series.max(), 100000))
        except Exception:
            min_price, max_price = 0, 100000
        if min_price > max_price:
            min_price, max_price = 0, 100000
        price_range = st.slider("가격(원)", min_value=min_price, max_value=max_price, value=(min_price, max_price))
        only_grain_free = st.checkbox("그레인프리만", value=False)
        only_vet_diet   = st.checkbox("수의학적 처방식만", value=False)
        topn_food  = st.number_input("사료 표시 개수", 1, 60, 12)
        topn_treat = st.number_input("간식 표시 개수", 1, 60, 8)
        if st.button("◀ 입력 화면으로 돌아가기", use_container_width=True):
            st.session_state.step = 1
            st.rerun()

    def selected_or_all(selected, all_values, all_label="전체"):
        if (not selected) or (all_label in selected):
            return list(all_values)
        return [x for x in selected if x != all_label]

    df = data.copy()

    brands_all = sorted([b for b in data["brand"].dropna().unique() if b])
    selected_brands = selected_or_all(f.get("sel_brands", []), brands_all)
    if selected_brands:
        df = df[df["brand"].isin(selected_brands)]

    price_all = ["저가","중간","프리미엄"]
    selected_prices = selected_or_all(f.get("sel_prices", []), price_all)
    if selected_prices:
        df = df[df["price_tier"].isin(selected_prices)]

    texture_all = ["드라이","습식/파우치"]
    selected_textures = selected_or_all(f.get("sel_textures", []), texture_all)
    if selected_textures:
        df = df[df["texture"].isin(selected_textures)]

    protein_all = ["닭","어류","소","오리","양","칠면조"]
    selected_proteins = selected_or_all(f.get("sel_proteins", []), protein_all)
    if selected_proteins:
        df = df[df["protein"].isin(selected_proteins)]

    if "price_krw" in df.columns:
        df = df[(df["price_krw"].fillna(0)>=price_range[0]) & (df["price_krw"].fillna(0)<=price_range[1])]
    if only_grain_free and "grain_free" in df.columns:
        df = df[df["grain_free"]==True]
    if only_vet_diet and "veterinary_diet" in df.columns:
        df = df[df["veterinary_diet"]==True]

    def score_row(row):
        score, reasons = 0.0, []
        if row.get("price_tier") in selected_prices:
            score += 0.5; reasons.append(f"{row.get('price_tier')} 가격")
        if row.get("texture") in selected_textures:
            score += 0.5; reasons.append(f"{row.get('texture')} 형태")
        if row.get("protein") in selected_proteins:
            score += 0.5; reasons.append(f"{row.get('protein')} 단백질")

        tags = set(str(row.get("tags","")).split(";"))
        if stage == "키튼" and "키튼" in tags: score += 1.5; reasons.append("키튼용")
        if stage == "시니어" and "시니어" in tags: score += 1.5; reasons.append("시니어용")

        kcal100 = row.get("kcal_per_100g")
        moisture = row.get("moisture_pct")
        mg100kcal = row.get("magnesium_mg_per_100kcal")
        phosphorus = row.get("phosphorus_pct_dm")
        sodium = row.get("sodium_pct_dm")

        if "비만 경향" in f.get("conditions", []) and pd.notna(kcal100) and kcal100 <= 330:
            score += 1.5; reasons.append("저칼로리")
        if "FLUTD/요로기계" in f.get("conditions", []):
            if (isinstance(row.get("texture",""), str) and str(row.get("texture","")).startswith("습식")) or (pd.notna(moisture) and moisture >= 70):
                score += 1.5; reasons.append("높은 수분")
            if pd.notna(mg100kcal) and mg100kcal <= 25:
                score += 1.0; reasons.append("Mg 낮음")
        if "신장 질환(CKD)" in f.get("conditions", []):
            if pd.notna(phosphorus) and phosphorus <= 0.6:
                score += 1.0; reasons.append("낮은 인")
            if pd.notna(sodium) and sodium <= 0.4:
                score += 0.8; reasons.append("적절한 Na")
        if "소화 민감성/IBD" in f.get("conditions", []) and "소화 민감성" in tags:
            score += 1.0; reasons.append("소화에 순함")
        if "헤어볼" in f.get("conditions", []) and "헤어볼" in tags:
            score += 1.0; reasons.append("헤어볼 관리")
        if f.get("activity")=="높음" and pd.notna(kcal100) and kcal100>=360:
            score += 0.7; reasons.append("활동량 높음 적합")
        if "고단백" in tags:
            score += 0.6; reasons.append("고단백")

        blob = " ".join([str(row.get("name","")), str(row.get("protein","")), str(row.get("ingredients",""))]).lower()
        if any(a in blob for a in expanded):
            score -= 5; reasons.append("알러지 의심 성분")

        _id = item_id(row)
        if _id in st.session_state.dislikes:
            score -= 2; reasons.append("비선호 항목")
        if _id in st.session_state.favorites:
            score += 0.5; reasons.append("즐겨찾기 가산")
        return score, reasons

    scores, reasons_all = [], []
    for _, r in df.iterrows():
        s, rs = score_row(r); scores.append(s); reasons_all.append(rs)
    df = df.assign(score=scores, reasons=reasons_all)

    tab_food, tab_treat, tab_favs, tab_dislikes, tab_table = st.tabs(["🍽 사료 추천", "🍘 간식 추천", "⭐ 즐겨찾기", "🚫 비선호", "📋 전체 표"])

    def render_cards(sub, is_treat=False, topn=10, show_actions=True):
        if sub.empty:
            st.warning("조건에 맞는 항목이 없습니다. 필터를 조정해 보세요.")
            return
        show = sub.sort_values("score", ascending=False).head(topn)
        cols = st.columns(3)
        for i, row in show.reset_index(drop=True).iterrows():
            _id = item_id(row)
            with cols[i % 3]:
                with st.container():
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    st.markdown(f"<h3>{row.get('name','(이름 없음)')}</h3>", unsafe_allow_html=True)
                    # 이미지 제거: 제품 이미지를 표시하지 않습니다.
                    st.markdown(f"<div class='meta'>브랜드: {row.get('brand','')} · 형태: {row.get('texture','')} · 단백질: {row.get('protein','')}</div>", unsafe_allow_html=True)
                    st.write(f"점수: **{round(float(row.get('score',0)),2)}** · 가격대: **{row.get('price_tier','')}**")
                    kcal100 = row.get("kcal_per_100g")
                    if not is_treat and pd.notna(kcal100) and kcal100>0:
                        grams = int(round(daily_kcal / kcal100 * 100))
                        st.success(f"권장 1일 급여량(사료): **약 {grams} g/일**")
                    if is_treat:
                        budget = int(daily_kcal*0.1)
                        per_piece = row.get("treat_kcal_per_piece")
                        if pd.notna(per_piece) and per_piece and per_piece>0:
                            count = max(1, budget//int(per_piece))
                            st.info(f"간식 한도 ≈ {budget} kcal → **하루 {count}개** (1개당 {int(per_piece)} kcal)")
                        else:
                            st.info(f"간식 한도 ≈ {budget} kcal · (CSV에 treat_kcal_per_piece를 넣으면 개수 계산)")
                    tags = [t for t in str(row.get("tags","")).split(";") if t]
                    if tags:
                        st.markdown("".join([f"<span class='pill tag'>{t}</span>" for t in tags]), unsafe_allow_html=True)
                    if row.get("reasons"):
                        st.markdown("<div class='small muted'>추천 이유: " + ", ".join(row["reasons"]) + "</div>", unsafe_allow_html=True)
                    product_url = row.get("product_url","")
                    if isinstance(product_url, str) and product_url.startswith("http"):
                        st.link_button("상품 보기", product_url)
                    if show_actions:
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            if st.button(("★ 즐겨찾기 해제" if _id in st.session_state.favorites else "⭐ 즐겨찾기"), key=f"fav_{_id}"):
                                if _id in st.session_state.favorites:
                                    st.session_state.favorites.remove(_id)
                                else:
                                    st.session_state.favorites.add(_id)
                                st.rerun()
                        with c2:
                            if st.button(("비선호 해제" if _id in st.session_state.dislikes else "🚫 비선호"), key=f"dis_{_id}"):
                                if _id in st.session_state.dislikes:
                                    st.session_state.dislikes.remove(_id)
                                else:
                                    st.session_state.dislikes.add(_id)
                                    if _id in st.session_state.favorites:
                                        st.session_state.favorites.remove(_id)
                                st.rerun()
                        with c3:
                            if st.button("🧹 숨기기", key=f"hide_{_id}"):
                                st.session_state.dislikes.add(_id)
                                if _id in st.session_state.favorites:
                                    st.session_state.favorites.remove(_id)
                                st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

    with tab_food:
        render_cards(df[df.get("type")=="사료"], is_treat=False, topn=int(topn_food))
    with tab_treat:
        render_cards(df[df.get("type")=="간식"], is_treat=True, topn=int(topn_treat))

    with tab_favs:
        fav_df = df[df.apply(lambda r: item_id(r) in st.session_state.favorites, axis=1)]
        render_cards(fav_df, is_treat=False, topn=len(fav_df) if len(fav_df)>0 else 0, show_actions=True)

    with tab_dislikes:
        dis_df = df[df.apply(lambda r: item_id(r) in st.session_state.dislikes, axis=1)]
        render_cards(dis_df, is_treat=False, topn=len(dis_df) if len(dis_df)>0 else 0, show_actions=True)

    with tab_table:
        st.dataframe(df, use_container_width=True)

    st.markdown("---")
    colx, coly = st.columns(2)
    with colx:
        st.download_button("⭐ 즐겨찾기 목록 CSV 다운로드",
                           df[df.apply(lambda r: item_id(r) in st.session_state.favorites, axis=1)].to_csv(index=False).encode('utf-8-sig'),
                           "favorites.csv", "text/csv")
    with coly:
        st.download_button("🚫 비선호 목록 CSV 다운로드",
                           df[df.apply(lambda r: item_id(r) in st.session_state.dislikes, axis=1)].to_csv(index=False).encode('utf-8-sig'),
                           "dislikes.csv", "text/csv")
