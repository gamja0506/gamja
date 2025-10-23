
# cat_app_v3.py
# -*- coding: utf-8 -*-
import math
import pandas as pd
import streamlit as st

st.set_page_config(page_title="🐱 고양이 맞춤 추천앱 V3", page_icon="🐾", layout="wide")

# ----------------- Global Styles -----------------
st.markdown("""
    <style>
    .block-container {padding-top: 2rem; padding-bottom: 2rem;}
    .small {font-size: 0.9rem; color: #666;}
    .card h3, .card h4 { margin: 0.2rem 0 0.4rem 0;}
    .product-img {border-radius: 12px; width: 100%; height: auto; object-fit: cover;}
    .muted {color:#6b7280;}
    .pill {display:inline-block;padding:.15rem .5rem;border-radius:9999px;background:#F3F4F6;margin-right:.25rem;font-size:.75rem;}
    .tag {background:#EEF2FF;color:#4F46E5;}
    .reason {background:#ECFDF5;color:#065F46;}
    .score {font-weight:700;}
    .section {padding: .6rem .8rem; background:#FAFAFA; border:1px solid #EEE; border-radius:14px;}
    </style>
""", unsafe_allow_html=True)

# ----------------- Load Data -----------------
@st.cache_data
def load_catalog(path: str):
    df = pd.read_csv(path)
    # Normalize dtypes
    text_cols = ["brand","name","type","texture","protein","ingredients","price_tier","tags","category","country","product_url","image_url","availability_region","sku"]
    for c in text_cols:
        if c in df.columns: df[c] = df[c].astype(str).fillna("")
    num_cols = ["moisture_pct","kcal_per_100g","magnesium_mg_per_100kcal","phosphorus_pct_dm","sodium_pct_dm",
                "crude_protein_pct_dm","crude_fat_pct_dm","crude_fiber_pct_dm","ash_pct_dm","omega3_pct_dm","calcium_pct_dm",
                "package_size_g","price_krw","palatability_score","rating_count","treat_kcal_per_piece"]
    for c in num_cols:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce")
    # booleans
    for c in ["grain_free","single_protein","veterinary_diet","indoor_suitable","neutered_suitable"]:
        if c in df.columns: df[c] = df[c].astype(str).str.lower().isin(["true","1","y","yes"])
    return df

DEFAULT_PATHS = ["catalog.csv", "real_brands_catalog_max.csv"]
data = None
for p in DEFAULT_PATHS:
    try:
        data = load_catalog(p); break
    except Exception: pass
if data is None:
    st.error("카탈로그 CSV를 찾지 못했어요. 폴더에 catalog.csv를 넣거나 파일 업로드를 사용하세요.")
    uploaded = st.file_uploader("카탈로그 CSV 업로드", type=["csv"])
    if uploaded:
        data = pd.read_csv(uploaded)
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
        if not t: continue
        expanded.add(t)
        for syns in ALLERGY_SYNONYMS.values():
            if t in [s.lower() for s in syns]:
                expanded.update([s.lower() for s in syns])
    return expanded

def life_stage(age):
    return "키튼" if age < 1 else ("어덜트" if age < 10 else "시니어")

def estimate_daily_kcal(weight, activity, neutered, stage):
    rer = 70 * (weight ** 0.75)
    factor = 1.0
    if neutered == "예": factor -= 0.05
    if activity == "낮음": factor -= 0.1
    elif activity == "높음": factor += 0.15
    if stage == "키튼": factor += 0.25
    elif stage == "시니어": factor -= 0.05
    return max(120, int(round(rer * factor)))

if "step" not in st.session_state: st.session_state.step = 1
if "form" not in st.session_state: st.session_state.form = {}

# ----------------- STEP 1 -----------------
if st.session_state.step == 1:
    st.title("1단계 · 반려묘 정보 입력")
    st.caption("왼쪽이 아니라 첫 페이지에서 입력 → 다음 화면에서 추천을 보여줍니다.")

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

        st.markdown("#### 알러지")
        c4, c5 = st.columns(2)
        with c4:
            base_allergy = st.multiselect("자주 있는 알러지", list(ALLERGY_SYNONYMS.keys()), key="f_base_allergy")
        with c5:
            custom_allergy = st.text_input("기타 알러지(쉼표 , 로 구분)", key="f_custom_allergy")

        st.markdown("---")
        st.markdown("#### 기본 필터 (선택)")
        brands = sorted([b for b in data["brand"].dropna().unique() if b])
        sel_brands = st.multiselect("브랜드", brands, default=[], key="f_sel_brands")
        price_opts = ["저가","중간","프리미엄"]
        sel_prices = st.multiselect("가격대", price_opts, default=price_opts, key="f_sel_prices")
        textures = ["드라이","습식/파우치"]
        sel_textures = st.multiselect("형태", textures, default=textures, key="f_sel_textures")
        proteins = ["닭","어류","소","오리","양","칠면조"]
        sel_proteins = st.multiselect("단백질", proteins, default=proteins, key="f_sel_proteins")

        submitted = st.form_submit_button("다음 단계 → 추천 보기", use_container_width=True)
        if submitted:
            st.session_state.form = dict(
                weight=weight, age=age, neutered=neutered, activity=activity, conditions=conditions,
                base_allergy=base_allergy, custom_allergy=custom_allergy, sel_brands=sel_brands,
                sel_prices=sel_prices, sel_textures=sel_textures, sel_proteins=sel_proteins
            )
            st.session_state.step = 2
            st.experimental_rerun()

    st.info("필요하면 언제든 이 페이지로 돌아와 값을 수정하고 다시 추천을 받을 수 있어요.")

# ----------------- STEP 2 -----------------
if st.session_state.step == 2:
    st.title("2단계 · 맞춤 추천 결과")
    f = st.session_state.form
    stage = life_stage(f["age"])
    daily_kcal = estimate_daily_kcal(f["weight"], f["activity"], f["neutered"], stage)
    st.success(f"권장 1일 필요 열량: **약 {daily_kcal} kcal/일** (간식은 보통 {int(daily_kcal*0.1)} kcal 이하) · 생애주기: **{stage}**")

    custom_tokens = [t.strip() for t in f.get("custom_allergy","").split(",") if t.strip()]
    allergies = set([a.lower() for a in f.get("base_allergy",[])]) | set([t.lower() for t in custom_tokens])
    expanded = expand_allergy_terms(allergies)

    with st.sidebar:
        st.header("🔎 추가 필터")
        min_price = int(data.get("price_krw", pd.Series([0])).fillna(0).min())
        max_price = int(data.get("price_krw", pd.Series([100000])).fillna(0).max())
        max_price = max(max_price, 100000)
        price_range = st.slider("가격(원)", min_value=min_price, max_value=max_price, value=(min_price, max_price))
        only_grain_free = st.checkbox("그레인프리만", value=False)
        only_vet_diet   = st.checkbox("수의학적 처방식만", value=False)
        topn_food  = st.number_input("사료 표시 개수", 1, 50, 12)
        topn_treat = st.number_input("간식 표시 개수", 1, 50, 8)
        if st.button("◀ 입력 화면으로 돌아가기", use_container_width=True):
            st.session_state.step = 1
            st.experimental_rerun()

    df = data.copy()
    if f["sel_brands"]: df = df[df["brand"].isin(f["sel_brands"])]
    if f["sel_prices"]: df = df[df["price_tier"].isin(f["sel_prices"])]
    if f["sel_textures"]: df = df[df["texture"].isin(f["sel_textures"])]
    if f["sel_proteins"]: df = df[df["protein"].isin(f["sel_proteins"])]
    if "price_krw" in df.columns:
        df = df[(df["price_krw"].fillna(0)>=price_range[0]) & (df["price_krw"].fillna(0)<=price_range[1])]
    if only_grain_free and "grain_free" in df.columns: df = df[df["grain_free"]==True]
    if only_vet_diet   and "veterinary_diet" in df.columns: df = df[df["veterinary_diet"]==True]

    def score_row(row):
        score, reasons = 0.0, []
        if row.get("price_tier") in f["sel_prices"]: score += 0.5; reasons.append(f"{row.get('price_tier')} 가격")
        if row.get("texture") in f["sel_textures"]: score += 0.5; reasons.append(f"{row.get('texture')} 형태")
        if row.get("protein") in f["sel_proteins"]: score += 0.5; reasons.append(f"{row.get('protein')} 단백질")
        tags = set(str(row.get("tags","")).split(";"))
        if stage == "키튼" and "키튼" in tags: score += 1.5; reasons.append("키튼용")
        if stage == "시니어" and "시니어" in tags: score += 1.5; reasons.append("시니어용")
        if "비만 경향" in f["conditions"] and pd.notna(row.get("kcal_per_100g")) and row.get("kcal_per_100g")<=330:
            score += 1.5; reasons.append("저칼로리")
        if "FLUTD/요로기계" in f["conditions"]:
            if str(row.get("texture","")).startswith("습식") or (pd.notna(row.get("moisture_pct")) and row.get("moisture_pct")>=70):
                score += 1.5; reasons.append("높은 수분")
            if pd.notna(row.get("magnesium_mg_per_100kcal")) and row.get("magnesium_mg_per_100kcal")<=25:
                score += 1.0; reasons.append("Mg 낮음")
        if "신장 질환(CKD)" in f["conditions"]:
            if pd.notna(row.get("phosphorus_pct_dm")) and row.get("phosphorus_pct_dm")<=0.6:
                score += 1.0; reasons.append("낮은 인")
            if pd.notna(row.get("sodium_pct_dm")) and row.get("sodium_pct_dm")<=0.4:
                score += 0.8; reasons.append("적절한 Na")
        if "소화 민감성/IBD" in f["conditions"] and "소화 민감성" in tags:
            score += 1.0; reasons.append("소화에 순함")
        if "헤어볼" in f["conditions"] and "헤어볼" in tags:
            score += 1.0; reasons.append("헤어볼 관리")
        if f["activity"]=="높음" and pd.notna(row.get("kcal_per_100g")) and row.get("kcal_per_100g")>=360:
            score += 0.7; reasons.append("활동량 높음 적합")
        if "고단백" in tags: score += 0.6; reasons.append("고단백")
        blob = " ".join([str(row.get("name","")), str(row.get("protein","")), str(row.get("ingredients",""))]).lower()
        if any(a in blob for a in expanded): score -= 5; reasons.append("알러지 의심 성분")
        return score, reasons

    scores, reasons_all = [], []
    for _, r in df.iterrows():
        s, rs = score_row(r); scores.append(s); reasons_all.append(rs)
    df = df.assign(score=scores, reasons=reasons_all)

    tab_food, tab_treat, tab_table = st.tabs(["🍽 사료 추천", "🍘 간식 추천", "📋 전체 표"])

    def render_cards(sub, is_treat=False, topn=10):
        if sub.empty:
            st.warning("조건에 맞는 항목이 없습니다. 필터를 조정해 보세요.")
            return
        show = sub.sort_values("score", ascending=False).head(topn)
        cols = st.columns(3)
        for i, row in show.reset_index(drop=True).iterrows():
            with cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"### {row['name']}")
                    img = row.get("image_url","")
                    if isinstance(img, str) and img.startswith("http"):
                        st.image(img, use_column_width=True, caption=row.get("brand",""))
                    else:
                        seed = (row.get("sku") or row.get("name") or "cat").replace(" ","_")
                        st.image(f"https://picsum.photos/seed/{seed}/600/400", use_column_width=True, caption=row.get("brand",""))
                    st.caption(f"브랜드: {row['brand']} · 형태: {row['texture']} · 단백질: {row['protein']}")
                    st.write(f"점수: **{round(row['score'],2)}** · 가격대: **{row.get('price_tier','')}**")
                    if not is_treat and pd.notna(row.get("kcal_per_100g")) and row.get("kcal_per_100g")>0:
                        grams = int(round(daily_kcal / row["kcal_per_100g"] * 100))
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
                    if isinstance(row.get("product_url",""), str) and row["product_url"].startswith("http"):
                        st.link_button("상품 보기", row["product_url"])

    with tab_food:
        render_cards(df[df["type"]=="사료"], is_treat=False, topn=int(topn_food))
    with tab_treat:
        render_cards(df[df["type"]=="간식"], is_treat=True, topn=int(topn_treat))
    with tab_table:
        st.dataframe(df, use_container_width=True)
